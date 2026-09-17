import hashlib
import io
from datetime import UTC, datetime
from zipfile import ZipFile

import pytest

from oceanscope_api.ports.contracts import FetchedPortDataset, SourceDescriptor
from oceanscope_api.ports.parsers import (
    UnLocodeParser,
    WorldPortIndexParser,
    parse_unlocode_coordinates,
    parse_wpi_coordinate,
)
from oceanscope_api.provenance.models import RedistributionStatus

NOW = datetime(2026, 9, 17, tzinfo=UTC)
TEST_SOURCE = SourceDescriptor(
    slug="test-port-source",
    display_name="TEST DATA Port Source",
    official_url="https://example.test/ports",
    terms_url="https://example.test/terms",
    attribution_text="TEST DATA attribution",
    license_identifier="TEST-ONLY",
    redistribution_status=RedistributionStatus.ALLOWED,
    terms_reviewed_at=NOW,
)


def dataset(content: bytes, *, filename: str) -> FetchedPortDataset:
    return FetchedPortDataset(
        source=TEST_SOURCE,
        data_version="TEST DATA v1",
        schema_version="TEST DATA schema",
        source_url="https://example.test/ports/v1",
        filename=filename,
        content_type="application/octet-stream",
        content=content,
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        retrieved_at=NOW,
        published_at=NOW,
    )


def unlocode_zip(rows: list[str]) -> bytes:
    stream = io.BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("release/csv/UNLOCODE CodeListPart1.csv", "\n".join(rows))
    return stream.getvalue()


def test_unlocode_parser_keeps_only_ports_and_reports_bad_coordinates() -> None:
    content = unlocode_zip(
        [
            ",TS,,.TEST DATA COUNTRY,,,,,,,,",
            ",TS,TST,TEST DATA Port,TEST DATA Port,,1-------,AA,2609,,1234N 04530E,",
            ",TS,RD1,TEST DATA Road,TEST DATA Road,,--3-----,AA,2609,,1234N 04530E,",
            ",TS,BAD,TEST DATA Coarse Port,TEST DATA Coarse Port,,1-------,AA,2609,,bad,",
        ]
    )

    result = UnLocodeParser().parse(dataset(content, filename="test-data.zip"))

    assert result.records_received == 3
    assert result.records_skipped == 1
    assert result.records_rejected == 0
    assert len(result.records) == 2
    assert result.quality_counts == {"invalid_coordinate": 1}
    assert result.records[0].un_locode == "TSTST"
    assert result.records[0].latitude == pytest.approx(12.566667)
    assert result.records[0].longitude == pytest.approx(45.5)
    assert result.records[1].latitude is None
    assert result.records[1].quality_flags == ("invalid_coordinate",)


def test_wpi_parser_rejects_invalid_coordinates_without_zero_fallback() -> None:
    content = (
        "portNumber,portName,countryCode,latitude,longitude,unloCode,extra\n"
        '1,TEST DATA Port,TS,"12°34\'00""N","045°30\'00""E",TS TST,kept\n'
        "2,TEST DATA Invalid Port,TS,invalid,invalid,,kept\n"
    ).encode()

    result = WorldPortIndexParser().parse(dataset(content, filename="test-data.csv"))

    assert result.records_received == 2
    assert result.records_rejected == 1
    assert len(result.records) == 1
    assert result.quality_counts == {"invalid_coordinate": 1}
    assert result.records[0].source_record_id == "1"
    assert result.records[0].un_locode == "TSTST"
    assert result.records[0].raw_record["extra"] == "kept"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0000N 00000E", (0.0, 0.0)), ("9000S 18000W", (-90.0, -180.0))],
)
def test_unlocode_coordinate_boundaries(value: str, expected: tuple[float, float]) -> None:
    assert parse_unlocode_coordinates(value) == expected


@pytest.mark.parametrize("value", ["9060N 18000E", "9001N 18000E", "not-a-coordinate"])
def test_unlocode_coordinates_reject_out_of_range_values(value: str) -> None:
    with pytest.raises(ValueError):
        parse_unlocode_coordinates(value)


def test_wpi_coordinate_respects_axis_and_hemisphere() -> None:
    assert parse_wpi_coordinate("12°30'00\"S", latitude=True) == -12.5
    assert parse_wpi_coordinate("045°15'30\"E", latitude=False) == pytest.approx(45.25833333)

    with pytest.raises(ValueError):
        parse_wpi_coordinate("181°00'00\"E", latitude=False)
    with pytest.raises(ValueError):
        parse_wpi_coordinate("045°00'00\"N", latitude=False)
