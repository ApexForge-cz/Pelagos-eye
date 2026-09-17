import csv
import hashlib
import io
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
import zstandard
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from oceanscope_api.earthquakes.artifacts import EarthquakeArtifactStore
from oceanscope_api.earthquakes.contracts import FetchedEarthquakeFeed
from oceanscope_api.earthquakes.parser import UsgsEarthquakeParser
from oceanscope_api.earthquakes.provider import USGS_SOURCE
from oceanscope_api.earthquakes.service import EarthquakeImportService
from oceanscope_api.history.artifacts import HistoricalAisArtifactStore
from oceanscope_api.history.contracts import FetchedHistoricalAisArchive, HistoricalAisRequest
from oceanscope_api.history.parser import MarineCadastreCsvParser
from oceanscope_api.history.provider import MARINE_CADASTRE_SOURCE
from oceanscope_api.history.service import HistoricalAisImportService
from oceanscope_api.ocean.artifacts import MarineForecastArtifactStore
from oceanscope_api.ocean.contracts import FetchedMarineForecast, MarineForecastRequest
from oceanscope_api.ocean.parser import OpenMeteoMarineParser
from oceanscope_api.ocean.provider import OPEN_METEO_MARINE_SOURCE
from oceanscope_api.ocean.service import MarineForecastImportService
from oceanscope_api.ports.artifacts import LocalArtifactStore
from oceanscope_api.ports.contracts import FetchedPortDataset, SourceDescriptor
from oceanscope_api.ports.parsers import WorldPortIndexParser
from oceanscope_api.ports.service import PortImportService
from oceanscope_api.provenance.models import RedistributionStatus

TEST_DATABASE_URL = os.getenv("OCEANSCOPE_TEST_DATABASE_URL")
API_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
@pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="OCEANSCOPE_TEST_DATABASE_URL must name an explicit disposable test database",
)
def test_provenance_migration_round_trip(tmp_path: Path) -> None:
    assert TEST_DATABASE_URL is not None
    database_name = make_url(TEST_DATABASE_URL).database or ""
    assert database_name.lower().endswith("_test"), (
        "migration test requires a database name ending in _test"
    )

    configuration = Config(str(API_ROOT / "alembic.ini"))
    configuration.set_main_option("sqlalchemy.url", TEST_DATABASE_URL.replace("%", "%%"))

    try:
        command.downgrade(configuration, "base")
        command.upgrade(configuration, "head")

        engine = create_engine(TEST_DATABASE_URL)
        try:
            assert {
                "alembic_version",
                "data_source",
                "source_version",
                "ingestion_run",
                "quality_issue",
                "port_source_record",
                "earthquake_event",
                "historical_ais_position",
                "marine_forecast_point",
            }.issubset(set(inspect(engine).get_table_names()))
            _assert_database_rejects_invalid_completed_run(engine)
            _assert_port_import_is_spatial_and_idempotent(engine, tmp_path)
            _assert_earthquake_import_is_spatial_and_idempotent(engine, tmp_path)
            _assert_marine_import_is_spatial_and_idempotent(engine, tmp_path)
            _assert_historical_ais_import_is_spatial_and_idempotent(engine, tmp_path)

            command.downgrade(configuration, "20260917_0001")
            assert not {
                "data_source",
                "source_version",
                "ingestion_run",
                "quality_issue",
                "port_source_record",
                "earthquake_event",
                "historical_ais_position",
                "marine_forecast_point",
            }.intersection(inspect(engine).get_table_names())
        finally:
            engine.dispose()
    finally:
        command.upgrade(configuration, "head")


def _assert_database_rejects_invalid_completed_run(engine: Engine) -> None:
    source_id = uuid4()
    now = datetime.now(UTC)

    with (
        pytest.raises(IntegrityError, match="completion_matches_status"),
        engine.begin() as connection,
    ):
        connection.execute(
            text(
                """
                INSERT INTO data_source (
                    id, slug, display_name, official_url, attribution_text,
                    redistribution_status, created_at, updated_at
                ) VALUES (
                    :id, :slug, 'TEST DATA Source', 'https://example.test/source',
                    'TEST DATA attribution', 'unreviewed', :now, :now
                )
                """
            ),
            {"id": source_id, "slug": f"test-source-{source_id.hex}", "now": now},
        )
        connection.execute(
            text(
                """
                INSERT INTO ingestion_run (
                    id, data_source_id, idempotency_key, status, source_state,
                    started_at, records_received, records_accepted, records_rejected,
                    parameters, code_revision, created_at
                ) VALUES (
                    :id, :source_id, 'invalid-completed-run', 'succeeded', 'LIVE',
                    :now, 0, 0, 0, '{}'::jsonb, 'TEST DATA revision', :now
                )
                """
            ),
            {"id": uuid4(), "source_id": source_id, "now": now},
        )


class _TestPortProvider:
    source = SourceDescriptor(
        slug="test-port-import",
        display_name="TEST DATA Port Import",
        official_url="https://example.test/ports",
        terms_url="https://example.test/terms",
        attribution_text="TEST DATA attribution",
        license_identifier="TEST-ONLY",
        redistribution_status=RedistributionStatus.ALLOWED,
        terms_reviewed_at=datetime(2026, 9, 17, tzinfo=UTC),
    )

    def __init__(self) -> None:
        self._content = (
            "portNumber,portName,countryCode,latitude,longitude,unloCode\n"
            '1,TEST DATA Port,TS,"12°34\'00""N","045°30\'00""E",TS TST\n'
        ).encode()

    def fetch(self) -> FetchedPortDataset:
        return FetchedPortDataset(
            source=self.source,
            data_version="TEST-DATA-v1",
            schema_version="TEST-DATA-schema-v1",
            source_url="https://example.test/ports/v1",
            filename="test-data.csv",
            content_type="text/csv",
            content=self._content,
            checksum_sha256=hashlib.sha256(self._content).hexdigest(),
            retrieved_at=datetime(2026, 9, 17, 1, tzinfo=UTC),
            published_at=datetime(2026, 9, 17, tzinfo=UTC),
        )


def _assert_port_import_is_spatial_and_idempotent(engine: Engine, tmp_path: Path) -> None:
    provider = _TestPortProvider()
    with Session(engine) as session:
        service = PortImportService(
            session,
            LocalArtifactStore(tmp_path),
            code_revision="TEST-DATA-revision",
        )
        first = service.import_dataset(provider, WorldPortIndexParser())
        second = service.import_dataset(provider, WorldPortIndexParser())

    assert first.status == "succeeded"
    assert first.records_accepted == 1
    assert second.ingestion_run_id == first.ingestion_run_id

    with engine.connect() as connection:
        count, srid = connection.execute(
            text("SELECT count(*), min(ST_SRID(location::geometry)) FROM port_source_record")
        ).one()
    assert count == 1
    assert srid == 4326


class _TestEarthquakeProvider:
    source = USGS_SOURCE

    def __init__(self) -> None:
        self._generated = 1_789_632_000_000
        self._updated = 1_789_631_940_000

    def fetch(self) -> FetchedEarthquakeFeed:
        import json

        document = {
            "type": "FeatureCollection",
            "metadata": {"generated": self._generated, "count": 1, "api": "TEST-DATA"},
            "features": [
                {
                    "type": "Feature",
                    "id": "test-event",
                    "properties": {
                        "mag": 2.5,
                        "place": "TEST DATA event",
                        "time": 1_789_631_900_000,
                        "updated": self._updated,
                        "status": "reviewed",
                        "tsunami": 0,
                        "sig": 100,
                        "type": "earthquake",
                        "detail": "https://example.test/event",
                    },
                    "geometry": {"type": "Point", "coordinates": [120.5, 30.25, 8.0]},
                }
            ],
        }
        content = json.dumps(document).encode()
        return FetchedEarthquakeFeed(
            source=self.source,
            data_version=f"TEST-DATA-{self._generated}",
            schema_version="TEST-DATA-schema",
            source_url="https://example.test/usgs-feed",
            content=content,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            generated_at=datetime.fromtimestamp(self._generated / 1000, tz=UTC),
            retrieved_at=datetime.fromtimestamp(self._generated / 1000, tz=UTC),
        )


def _assert_earthquake_import_is_spatial_and_idempotent(engine: Engine, tmp_path: Path) -> None:
    provider = _TestEarthquakeProvider()
    with Session(engine) as session:
        service = EarthquakeImportService(
            session,
            EarthquakeArtifactStore(tmp_path),
            code_revision="TEST-DATA-revision",
        )
        first = service.import_feed(provider, UsgsEarthquakeParser())
        second = service.import_feed(provider, UsgsEarthquakeParser())
        provider._generated += 60_000
        provider._updated += 60_000
        revised = service.import_feed(provider, UsgsEarthquakeParser())

    assert first.status == "succeeded"
    assert first.inserted == 1
    assert second.ingestion_run_id == first.ingestion_run_id
    assert revised.updated == 1

    with engine.connect() as connection:
        count, srid, magnitude = connection.execute(
            text(
                "SELECT count(*), min(ST_SRID(location::geometry)), max(magnitude) "
                "FROM earthquake_event"
            )
        ).one()
    assert count == 1
    assert srid == 4326
    assert magnitude == 2.5


class _TestMarineProvider:
    source = OPEN_METEO_MARINE_SOURCE

    def fetch(self, request: MarineForecastRequest) -> FetchedMarineForecast:
        import json

        document = {
            "latitude": 20.041664,
            "longitude": -40.041656,
            "utc_offset_seconds": 0,
            "timezone": "GMT",
            "hourly_units": {
                "time": "iso8601",
                "wave_height": "m",
                "wave_direction": "°",
                "wave_period": "s",
                "sea_surface_temperature": "°C",
                "ocean_current_velocity": "km/h",
                "ocean_current_direction": "°",
                "sea_level_height_msl": "m",
            },
            "hourly": {
                "time": ["2026-09-17T12:00"],
                "wave_height": [1.4],
                "wave_direction": [71],
                "wave_period": [7.55],
                "sea_surface_temperature": [27.6],
                "ocean_current_velocity": [0.5],
                "ocean_current_direction": [225],
                "sea_level_height_msl": [0.19],
            },
        }
        content = json.dumps(document).encode()
        return FetchedMarineForecast(
            source=self.source,
            request=request,
            data_version="TEST-DATA-marine-v1",
            schema_version="TEST-DATA-schema",
            source_url="https://example.test/marine",
            content=content,
            checksum_sha256=hashlib.sha256(content).hexdigest(),
            retrieved_at=datetime(2026, 9, 17, 12, tzinfo=UTC),
        )


def _assert_marine_import_is_spatial_and_idempotent(engine: Engine, tmp_path: Path) -> None:
    request = MarineForecastRequest(latitude=20, longitude=-40, forecast_hours=1)
    with Session(engine) as session:
        service = MarineForecastImportService(
            session,
            MarineForecastArtifactStore(tmp_path),
            code_revision="TEST-DATA-revision",
        )
        first = service.import_forecast(_TestMarineProvider(), OpenMeteoMarineParser(), request)
        second = service.import_forecast(_TestMarineProvider(), OpenMeteoMarineParser(), request)

    assert first.status == "succeeded"
    assert first.inserted == 1
    assert second.ingestion_run_id == first.ingestion_run_id

    with engine.connect() as connection:
        count, srid, height = connection.execute(
            text(
                "SELECT count(*), min(ST_SRID(location::geometry)), max(wave_height_m) "
                "FROM marine_forecast_point"
            )
        ).one()
    assert count == 1
    assert srid == 4326
    assert height == 1.4


class _TestHistoricalAisProvider:
    source = MARINE_CADASTRE_SOURCE

    def __init__(self, tmp_path: Path) -> None:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
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
        )
        writer.writerow(
            [
                "123456789",
                "2024-01-14T00:10:00",
                "29.0",
                "-90.0",
                "10.5",
                "90",
                "91",
                "TEST DATA VESSEL",
                "IMO1234567",
                "TEST123",
                "70",
                "0",
                "100",
                "20",
                "6.5",
                "70",
                "A",
            ]
        )
        self._content = zstandard.ZstdCompressor().compress(output.getvalue().encode())
        self._path = tmp_path / "TEST-DATA-history.csv.zst"
        self._path.write_bytes(self._content)

    def fetch(self, request: HistoricalAisRequest) -> FetchedHistoricalAisArchive:
        return FetchedHistoricalAisArchive(
            source=self.source,
            request=request,
            data_version="TEST-DATA-history-v1",
            schema_version="TEST-DATA-schema",
            source_url="https://example.test/history",
            archive_path=self._path,
            checksum_sha256=hashlib.sha256(self._content).hexdigest(),
            size_bytes=len(self._content),
            retrieved_at=datetime(2026, 9, 17, 12, tzinfo=UTC),
        )


def _assert_historical_ais_import_is_spatial_and_idempotent(engine: Engine, tmp_path: Path) -> None:
    request = HistoricalAisRequest(
        archive_date=datetime(2024, 1, 14, tzinfo=UTC).date(),
        min_longitude=-91,
        min_latitude=28,
        max_longitude=-89,
        max_latitude=30,
        start_at=datetime(2024, 1, 14, 0, tzinfo=UTC),
        end_at=datetime(2024, 1, 14, 1, tzinfo=UTC),
        record_limit=10,
    )
    provider = _TestHistoricalAisProvider(tmp_path)
    with Session(engine) as session:
        service = HistoricalAisImportService(
            session,
            HistoricalAisArtifactStore(tmp_path),
            code_revision="TEST-DATA-revision",
        )
        first = service.import_archive(provider, MarineCadastreCsvParser(), request)
        second = service.import_archive(provider, MarineCadastreCsvParser(), request)

    assert first.status == "succeeded"
    assert first.inserted == 1
    assert second.ingestion_run_id == first.ingestion_run_id

    with engine.connect() as connection:
        count, srid, mmsi = connection.execute(
            text(
                "SELECT count(*), min(ST_SRID(location::geometry)), max(mmsi) "
                "FROM historical_ais_position"
            )
        ).one()
    assert count == 1
    assert srid == 4326
    assert mmsi == "123456789"
