from datetime import UTC, datetime, timedelta
from uuid import UUID

from oceanscope_api.status.contracts import (
    IngestionRunSnapshot,
    QualityIssueSnapshot,
    SourceHistory,
    SourceVersionSnapshot,
)
from oceanscope_api.status.service import SourceStatusService, SystemStatusService

NOW = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)
SOURCE_VERSION_ID = UUID("00000000-0000-0000-0000-000000000001")
USABLE_RUN_ID = UUID("00000000-0000-0000-0000-000000000002")
FAILED_RUN_ID = UUID("00000000-0000-0000-0000-000000000003")


class StubRepository:
    def __init__(self, histories: list[SourceHistory]) -> None:
        self._histories = histories

    def list_source_histories(self) -> list[SourceHistory]:
        return self._histories


def base_history(
    *,
    runs: tuple[IngestionRunSnapshot, ...] = (),
    versions: tuple[SourceVersionSnapshot, ...] = (),
    issues: tuple[QualityIssueSnapshot, ...] = (),
) -> SourceHistory:
    return SourceHistory(
        slug="test-source",
        display_name="TEST DATA Source",
        official_url="https://example.test/source",
        terms_url="https://example.test/terms",
        attribution_text="TEST DATA attribution",
        license_identifier="TEST-ONLY",
        redistribution_status="allowed",
        versions=versions,
        runs=runs,
        quality_issues=issues,
    )


def test_source_without_ingestion_is_explicitly_unavailable() -> None:
    result = SourceStatusService(StubRepository([base_history()])).list_sources()[0]

    assert result.state == "OFFLINE"
    assert result.availability == "DATA UNAVAILABLE"
    assert result.has_usable_data is False
    assert result.latest_version is None


def test_failed_latest_run_does_not_relabel_older_data_as_live() -> None:
    version = SourceVersionSnapshot(
        id=SOURCE_VERSION_ID,
        data_version="TEST-DATA-1",
        schema_version="test-schema-v1",
        source_url="https://example.test/source/data.csv",
        published_at=NOW - timedelta(days=1),
        retrieved_at=NOW,
    )
    failed = IngestionRunSnapshot(
        id=FAILED_RUN_ID,
        source_version_id=None,
        status="failed",
        source_state="OFFLINE",
        cache_age_seconds=None,
        started_at=NOW + timedelta(hours=1),
        finished_at=NOW + timedelta(hours=1, minutes=1),
        records_received=0,
        records_accepted=0,
        records_rejected=0,
    )
    usable = IngestionRunSnapshot(
        id=USABLE_RUN_ID,
        source_version_id=SOURCE_VERSION_ID,
        status="partial",
        source_state="LIVE",
        cache_age_seconds=None,
        started_at=NOW,
        finished_at=NOW + timedelta(minutes=5),
        records_received=10,
        records_accepted=9,
        records_rejected=1,
    )
    issue = QualityIssueSnapshot(
        ingestion_run_id=USABLE_RUN_ID,
        code="invalid_coordinate",
        severity="warning",
        record_count=1,
        message="TEST DATA invalid coordinate",
    )

    result = SourceStatusService(
        StubRepository([base_history(runs=(failed, usable), versions=(version,), issues=(issue,))])
    ).list_sources()[0]

    assert result.state == "OFFLINE"
    assert result.availability == "AVAILABLE"
    assert result.has_usable_data is True
    assert result.latest_run == failed
    assert result.latest_usable_run == usable
    assert result.latest_version == version
    assert result.quality_issues == (issue,)


def test_system_status_reports_database_state_without_fallback_values() -> None:
    ready = SystemStatusService(lambda: True).get_status()
    degraded = SystemStatusService(lambda: False).get_status()

    assert ready.overall_state == "READY"
    assert ready.database.state == "LIVE"
    assert degraded.overall_state == "DEGRADED"
    assert degraded.database.state == "OFFLINE"
    assert degraded.database.detail == "DATA UNAVAILABLE"
