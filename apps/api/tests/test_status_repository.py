from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from oceanscope_api.db.base import Base
from oceanscope_api.provenance.models import (
    DataSource,
    IngestionRun,
    QualityIssue,
    SourceVersion,
)
from oceanscope_api.status.repository import SqlAlchemySourceStatusSummaryRepository

NOW = datetime(2026, 9, 20, 4, 0, tzinfo=UTC)


@pytest.fixture
def engine() -> Iterator[Engine]:
    database = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(
        database,
        tables=[
            Base.metadata.tables["data_source"],
            Base.metadata.tables["source_version"],
            Base.metadata.tables["ingestion_run"],
            Base.metadata.tables["quality_issue"],
        ],
    )
    yield database
    database.dispose()


def test_system_status_summary_is_bounded_by_source_count(engine: Engine) -> None:
    with Session(engine) as session:
        source = DataSource(
            slug="test-source",
            display_name="TEST DATA Source",
            official_url="https://example.test/source",
            terms_url="https://example.test/terms",
            attribution_text="TEST DATA attribution",
            license_identifier="TEST-ONLY",
            redistribution_status="allowed",
            terms_reviewed_at=NOW,
        )
        old_version = SourceVersion(
            data_source=source,
            data_version="TEST-DATA-OLD",
            schema_version="test-v1",
            source_url="https://example.test/old",
            published_at=NOW - timedelta(days=2),
            retrieved_at=NOW - timedelta(days=1),
        )
        current_version = SourceVersion(
            data_source=source,
            data_version="TEST-DATA-CURRENT",
            schema_version="test-v1",
            source_url="https://example.test/current",
            published_at=NOW - timedelta(hours=2),
            retrieved_at=NOW - timedelta(hours=1),
        )
        session.add_all([source, old_version, current_version])
        session.flush()

        for index in range(100):
            old_run = IngestionRun(
                data_source_id=source.id,
                source_version_id=old_version.id,
                idempotency_key=f"TEST-DATA-OLD-{index}",
                status="succeeded",
                source_state="LIVE",
                started_at=NOW - timedelta(days=1, minutes=index),
                finished_at=NOW - timedelta(days=1, minutes=index) + timedelta(seconds=1),
                records_received=1,
                records_accepted=1,
                records_rejected=0,
                parameters={},
                code_revision="test-revision",
            )
            session.add(old_run)
            session.flush()
            session.add(
                QualityIssue(
                    ingestion_run_id=old_run.id,
                    code="missing_required",
                    severity="warning",
                    record_count=1,
                    message="TEST DATA old issue",
                )
            )

        usable_run = IngestionRun(
            data_source_id=source.id,
            source_version_id=current_version.id,
            idempotency_key="TEST-DATA-CURRENT",
            status="partial",
            source_state="LIVE",
            started_at=NOW - timedelta(minutes=10),
            finished_at=NOW - timedelta(minutes=9),
            records_received=10,
            records_accepted=9,
            records_rejected=1,
            parameters={},
            code_revision="test-revision",
        )
        latest_failed_run = IngestionRun(
            data_source_id=source.id,
            source_version_id=None,
            idempotency_key="TEST-DATA-FAILED",
            status="failed",
            source_state="OFFLINE",
            started_at=NOW,
            finished_at=NOW + timedelta(seconds=1),
            records_received=0,
            records_accepted=0,
            records_rejected=0,
            parameters={},
            code_revision="test-revision",
            failure_reason="TEST DATA provider unavailable",
        )
        session.add_all([usable_run, latest_failed_run])
        session.flush()
        session.add(
            QualityIssue(
                ingestion_run_id=usable_run.id,
                code="invalid_coordinate",
                severity="warning",
                record_count=1,
                message="TEST DATA current issue",
            )
        )
        latest_failed_run_id = latest_failed_run.id
        usable_run_id = usable_run.id
        current_version_id = current_version.id
        session.commit()

    statement_count = 0

    def count_statement(*_args: object) -> None:
        nonlocal statement_count
        statement_count += 1

    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        with Session(engine) as session:
            histories = SqlAlchemySourceStatusSummaryRepository(session).list_source_histories()
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)

    assert statement_count == 4
    assert len(histories) == 1
    history = histories[0]
    assert [run.id for run in history.runs] == [latest_failed_run_id, usable_run_id]
    assert [version.id for version in history.versions] == [current_version_id]
    assert history.quality_issues == ()
