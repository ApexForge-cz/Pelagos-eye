import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import IntegrityError

from alembic import command

TEST_DATABASE_URL = os.getenv("OCEANSCOPE_TEST_DATABASE_URL")
API_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.integration
@pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="OCEANSCOPE_TEST_DATABASE_URL must name an explicit disposable test database",
)
def test_provenance_migration_round_trip() -> None:
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
            }.issubset(set(inspect(engine).get_table_names()))
            _assert_database_rejects_invalid_completed_run(engine)

            command.downgrade(configuration, "20260917_0001")
            assert not {
                "data_source",
                "source_version",
                "ingestion_run",
                "quality_issue",
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
