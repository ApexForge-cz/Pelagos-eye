from datetime import UTC, datetime, timedelta
from uuid import UUID

from oceanscope_api.core.errors import DatabaseUnavailableError
from oceanscope_api.status.contracts import (
    IngestionRunSnapshot,
    QualityIssueSnapshot,
    SourceHistory,
    SourceStatus,
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
    slug: str = "test-source",
    runs: tuple[IngestionRunSnapshot, ...] = (),
    versions: tuple[SourceVersionSnapshot, ...] = (),
    issues: tuple[QualityIssueSnapshot, ...] = (),
) -> SourceHistory:
    return SourceHistory(
        slug=slug,
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
    result = SourceStatusService(StubRepository([base_history()]), now=lambda: NOW).list_sources()[
        0
    ]

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
        StubRepository([base_history(runs=(failed, usable), versions=(version,), issues=(issue,))]),
        now=lambda: NOW + timedelta(hours=2),
    ).list_sources()[0]

    assert result.state == "CACHED"
    assert result.availability == "AVAILABLE"
    assert result.has_usable_data is True
    assert result.cache_age_seconds == 7200
    assert result.freshness.age_seconds == 7200
    assert result.latest_run == failed
    assert result.latest_usable_run == usable
    assert result.latest_version == version
    assert result.quality_issues == (issue,)


def test_usgs_freshness_transitions_from_delayed_to_cached_to_offline() -> None:
    version = SourceVersionSnapshot(
        id=SOURCE_VERSION_ID,
        data_version="TEST-DATA-1",
        schema_version="test-schema-v1",
        source_url="https://example.test/feed.geojson",
        published_at=NOW,
        retrieved_at=NOW,
    )
    usable = IngestionRunSnapshot(
        id=USABLE_RUN_ID,
        source_version_id=SOURCE_VERSION_ID,
        status="succeeded",
        source_state="LIVE",
        cache_age_seconds=None,
        started_at=NOW,
        finished_at=NOW,
        records_received=1,
        records_accepted=1,
        records_rejected=0,
    )
    history = base_history(slug="usgs-earthquakes", runs=(usable,), versions=(version,))

    delayed = SourceStatusService(
        StubRepository([history]), now=lambda: NOW + timedelta(minutes=10)
    ).list_sources()[0]
    cached = SourceStatusService(
        StubRepository([history]), now=lambda: NOW + timedelta(minutes=30)
    ).list_sources()[0]
    offline = SourceStatusService(
        StubRepository([history]), now=lambda: NOW + timedelta(hours=2)
    ).list_sources()[0]

    assert delayed.state == "DELAYED"
    assert delayed.cache_age_seconds is None
    assert cached.state == "CACHED"
    assert cached.cache_age_seconds == 1800
    assert offline.state == "OFFLINE"
    assert offline.availability == "DATA UNAVAILABLE"
    assert offline.has_usable_data is False


def test_immutable_historical_archive_cache_does_not_expire() -> None:
    version = SourceVersionSnapshot(
        id=SOURCE_VERSION_ID,
        data_version="TEST-DATA-archive",
        schema_version="test-schema-v1",
        source_url="https://example.test/archive.zst",
        published_at=None,
        retrieved_at=NOW,
    )
    cached_run = IngestionRunSnapshot(
        id=USABLE_RUN_ID,
        source_version_id=SOURCE_VERSION_ID,
        status="succeeded",
        source_state="CACHED",
        cache_age_seconds=864_000,
        started_at=NOW,
        finished_at=NOW,
        records_received=1,
        records_accepted=1,
        records_rejected=0,
    )

    result = SourceStatusService(
        StubRepository(
            [
                base_history(
                    slug="noaa-marinecadastre-ais",
                    runs=(cached_run,),
                    versions=(version,),
                )
            ]
        ),
        now=lambda: NOW + timedelta(days=500),
    ).list_sources()[0]

    assert result.state == "CACHED"
    assert result.availability == "AVAILABLE"
    assert result.freshness.cache_ttl_seconds is None
    assert result.cache_age_seconds == 44_064_000


def test_system_status_reports_database_state_without_fallback_values() -> None:
    source = SourceStatusService(StubRepository([base_history()]), now=lambda: NOW).list_sources()[
        0
    ]
    ready = SystemStatusService(
        lambda: True,
        lambda: True,
        lambda: [source],
        now=lambda: NOW,
    ).get_status()
    redis_degraded = SystemStatusService(
        lambda: True,
        lambda: False,
        lambda: [source],
        now=lambda: NOW,
    ).get_status()

    def unexpected_source_query() -> list[SourceStatus]:
        raise AssertionError("source query must be skipped")

    degraded = SystemStatusService(
        lambda: False,
        lambda: False,
        unexpected_source_query,
        now=lambda: NOW,
    ).get_status()

    assert ready.overall_state == "READY"
    assert ready.database.state == "LIVE"
    assert ready.redis.state == "LIVE"
    assert ready.checked_at == NOW
    assert ready.providers[0].slug == "test-source"
    assert ready.providers[0].state == "OFFLINE"
    assert ready.providers[0].availability == "DATA UNAVAILABLE"
    assert redis_degraded.overall_state == "DEGRADED"
    assert redis_degraded.database.state == "LIVE"
    assert redis_degraded.redis.state == "OFFLINE"
    assert len(redis_degraded.providers) == 1
    assert degraded.overall_state == "DEGRADED"
    assert degraded.database.state == "OFFLINE"
    assert degraded.database.detail == "DATA UNAVAILABLE"
    assert degraded.redis.state == "OFFLINE"
    assert degraded.redis.detail == "DATA UNAVAILABLE"
    assert degraded.providers == ()


def test_system_status_downgrades_database_when_provider_status_query_fails() -> None:
    def unavailable() -> list[SourceStatus]:
        raise DatabaseUnavailableError("TEST DATA database unavailable")

    result = SystemStatusService(
        lambda: True,
        lambda: True,
        unavailable,
        now=lambda: NOW,
    ).get_status()

    assert result.overall_state == "DEGRADED"
    assert result.database.state == "OFFLINE"
    assert result.providers == ()


def test_system_status_exposes_latest_provider_run_and_source_times() -> None:
    version = SourceVersionSnapshot(
        id=SOURCE_VERSION_ID,
        data_version="TEST-DATA-1",
        schema_version="test-schema-v1",
        source_url="https://example.test/feed.geojson",
        published_at=NOW - timedelta(minutes=1),
        retrieved_at=NOW,
    )
    run = IngestionRunSnapshot(
        id=USABLE_RUN_ID,
        source_version_id=SOURCE_VERSION_ID,
        status="partial",
        source_state="LIVE",
        cache_age_seconds=None,
        started_at=NOW,
        finished_at=NOW + timedelta(seconds=5),
        records_received=2,
        records_accepted=1,
        records_rejected=1,
    )
    source = SourceStatusService(
        StubRepository([base_history(slug="usgs-earthquakes", runs=(run,), versions=(version,))]),
        now=lambda: NOW + timedelta(minutes=10),
    ).list_sources()[0]

    result = SystemStatusService(
        lambda: True,
        lambda: True,
        lambda: [source],
        now=lambda: NOW + timedelta(minutes=10),
    ).get_status()
    provider = result.providers[0]

    assert provider.state == "DELAYED"
    assert provider.source_published_at == NOW - timedelta(minutes=1)
    assert provider.source_retrieved_at == NOW
    assert provider.latest_run == run
    assert provider.latest_run.records_accepted == 1
    assert provider.latest_run.records_rejected == 1
