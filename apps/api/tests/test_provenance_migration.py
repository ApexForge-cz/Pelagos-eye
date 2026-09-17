import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
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
            }.issubset(set(inspect(engine).get_table_names()))
            _assert_database_rejects_invalid_completed_run(engine)
            _assert_port_import_is_spatial_and_idempotent(engine, tmp_path)

            command.downgrade(configuration, "20260917_0001")
            assert not {
                "data_source",
                "source_version",
                "ingestion_run",
                "quality_issue",
                "port_source_record",
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
