import csv
import hashlib
import io
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import pytest
import zstandard

from oceanscope_api.history.contracts import (
    FetchedHistoricalAisArchive,
    HistoricalAisDownloadError,
    HistoricalAisRequest,
    HistoricalAisSchemaError,
)
from oceanscope_api.history.parser import MarineCadastreCsvParser
from oceanscope_api.history.provider import (
    MARINE_CADASTRE_SOURCE,
    MAX_ARCHIVE_BYTES,
    MarineCadastreProvider,
)
from oceanscope_api.provenance.models import SourceState

FIELDNAMES = [
    "MMSI",
    "BaseDateTime",
    "LAT",
    "LON",
    "SOG",
    "COG",
    "Heading",
    "VesselName",
    "IMO",
    "CallSign",
    "VesselType",
    "Status",
    "Length",
    "Width",
    "Draft",
    "Cargo",
    "TransceiverClass",
]


def request(*, record_limit: int = 10) -> HistoricalAisRequest:
    return HistoricalAisRequest(
        archive_date=date(2024, 1, 14),
        min_longitude=-91,
        min_latitude=28,
        max_longitude=-89,
        max_latitude=30,
        start_at=datetime(2024, 1, 14, 0, tzinfo=UTC),
        end_at=datetime(2024, 1, 14, 1, tzinfo=UTC),
        record_limit=record_limit,
    )


def row(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "MMSI": "123456789",
        "BaseDateTime": "2024-01-14T00:10:00",
        "LAT": "29.0",
        "LON": "-90.0",
        "SOG": "10.5",
        "COG": "360.0",
        "Heading": "511",
        "VesselName": "TEST DATA VESSEL",
        "IMO": "IMO1234567",
        "CallSign": "TEST123",
        "VesselType": "70",
        "Status": "0",
        "Length": "100",
        "Width": "20",
        "Draft": "6.5",
        "Cargo": "70",
        "TransceiverClass": "A",
    }
    values.update(changes)
    return values


def compressed_csv(rows: list[dict[str, Any]], *, fieldnames: list[str] | None = None) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames or FIELDNAMES, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return zstandard.ZstdCompressor().compress(output.getvalue().encode())


def archive(tmp_path: Path, content: bytes, import_request: HistoricalAisRequest) -> Any:
    path = tmp_path / "TEST-DATA.csv.zst"
    path.write_bytes(content)
    return FetchedHistoricalAisArchive(
        source=MARINE_CADASTRE_SOURCE,
        request=import_request,
        data_version="TEST-DATA",
        schema_version="TEST-DATA-schema",
        source_url="https://example.test/TEST-DATA.csv.zst",
        archive_path=path,
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        retrieved_at=datetime(2026, 9, 17, tzinfo=UTC),
    )


def test_request_rejects_unbounded_geography_and_time() -> None:
    with pytest.raises(ValueError, match="longitude span"):
        HistoricalAisRequest(
            archive_date=date(2024, 1, 14),
            min_longitude=-100,
            min_latitude=28,
            max_longitude=-89,
            max_latitude=30,
            start_at=datetime(2024, 1, 14, 0, tzinfo=UTC),
            end_at=datetime(2024, 1, 14, 1, tzinfo=UTC),
        )


def test_parser_filters_rejects_deduplicates_and_caps(tmp_path: Path) -> None:
    first = row()
    content = compressed_csv(
        [
            first,
            first,
            row(MMSI="223456789", LON="-80"),
            row(MMSI="323456789", LAT="bad"),
            row(MMSI="423456789", BaseDateTime="2024-01-14T00:20:00"),
        ]
    )

    parsed = MarineCadastreCsvParser().parse(archive(tmp_path, content, request(record_limit=1)))

    assert parsed.records_received == 5
    assert parsed.records_rejected == 1
    assert parsed.records_filtered == 1
    assert parsed.records_duplicate == 1
    assert parsed.records_capped == 1
    assert len(parsed.records) == 1
    assert parsed.quality_counts == {
        "coverage_unknown": 1,
        "duplicate": 1,
        "invalid_coordinate": 1,
    }
    assert parsed.records[0].cog_deg is None
    assert parsed.records[0].heading_deg is None
    assert parsed.records[0].quality_flags == ()


def test_parser_rejects_schema_drift(tmp_path: Path) -> None:
    columns = [name for name in FIELDNAMES if name != "MMSI"]
    content = compressed_csv([row()], fieldnames=columns)

    with pytest.raises(HistoricalAisSchemaError, match="MMSI"):
        MarineCadastreCsvParser().parse(archive(tmp_path, content, request()))


def test_parser_accepts_current_snake_case_bulk_schema(tmp_path: Path) -> None:
    aliases = {
        "MMSI": "mmsi",
        "BaseDateTime": "base_date_time",
        "LAT": "latitude",
        "LON": "longitude",
        "SOG": "sog",
        "COG": "cog",
        "Heading": "heading",
        "VesselName": "vessel_name",
        "IMO": "imo",
        "CallSign": "call_sign",
        "VesselType": "vessel_type",
        "Status": "status",
        "Length": "length",
        "Width": "width",
        "Draft": "draft",
        "Cargo": "cargo",
        "TransceiverClass": "transceiver",
    }
    current_row = {aliases[key]: value for key, value in row().items()}
    content = compressed_csv([current_row], fieldnames=list(current_row))

    parsed = MarineCadastreCsvParser().parse(archive(tmp_path, content, request()))

    assert len(parsed.records) == 1
    assert parsed.records[0].mmsi == "123456789"
    assert parsed.records[0].transceiver_class == "A"


def test_provider_constructs_only_verified_daily_archive_url(tmp_path: Path) -> None:
    content = compressed_csv([row()])

    def handler(http_request: httpx.Request) -> httpx.Response:
        parsed = urlparse(str(http_request.url))
        assert parsed.netloc == "noaaocm.blob.core.windows.net"
        assert parsed.path == "/ais/csv2/csv2024/ais-2024-01-14.csv.zst"
        return httpx.Response(200, content=content)

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        MarineCadastreProvider(tmp_path, client) as provider,
    ):
        fetched = provider.fetch(request())

    assert fetched.archive_path.read_bytes() == content
    assert fetched.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert fetched.size_bytes == len(content)


def test_provider_rejects_declared_oversized_archive(tmp_path: Path) -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, headers={"content-length": str(MAX_ARCHIVE_BYTES + 1)})

    with (
        httpx.Client(transport=httpx.MockTransport(handler)) as client,
        MarineCadastreProvider(tmp_path, client) as provider,
        pytest.raises(HistoricalAisDownloadError, match="download limit"),
    ):
        provider.fetch(request())


def test_provider_reuses_a_verified_local_archive(tmp_path: Path) -> None:
    content = compressed_csv([row()])
    local_archive = tmp_path / "official.csv.zst"
    local_archive.write_bytes(content)

    with MarineCadastreProvider(tmp_path / "downloads", local_archive=local_archive) as provider:
        fetched = provider.fetch(request())

    assert fetched.archive_path == local_archive
    assert fetched.checksum_sha256 == hashlib.sha256(content).hexdigest()
    assert fetched.source_state is SourceState.CACHED
    assert fetched.cache_age_seconds is not None
