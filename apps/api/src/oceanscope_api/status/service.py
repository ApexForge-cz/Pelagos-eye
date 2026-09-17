from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, cast

from oceanscope_api import __version__
from oceanscope_api.provenance.models import IngestionStatus
from oceanscope_api.status.contracts import (
    SourceAvailabilitySnapshot,
    SourceStatus,
    SourceStatusRepository,
    SystemDependencyStatus,
    SystemStatus,
)
from oceanscope_api.status.freshness import evaluate_freshness, policy_for


class SourceStatusService:
    def __init__(
        self,
        repository: SourceStatusRepository,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._repository = repository
        self._now = now or (lambda: datetime.now(UTC))

    def list_sources(self) -> list[SourceStatus]:
        results: list[SourceStatus] = []
        now = self._now()
        for history in self._repository.list_source_histories():
            latest_run = history.runs[0] if history.runs else None
            latest_usable_run = next(
                (
                    run
                    for run in history.runs
                    if run.status
                    in {IngestionStatus.SUCCEEDED.value, IngestionStatus.PARTIAL.value}
                    and run.source_version_id is not None
                ),
                None,
            )
            versions_by_id = {version.id: version for version in history.versions}
            usable_version_id = (
                latest_usable_run.source_version_id if latest_usable_run is not None else None
            )
            latest_version = (
                versions_by_id.get(usable_version_id) if usable_version_id is not None else None
            )
            freshness = evaluate_freshness(
                policy=policy_for(history.slug),
                latest_run=latest_run,
                usable_run=latest_usable_run,
                usable_version=latest_version,
                now=now,
            )
            usable_quality = (
                tuple(
                    issue
                    for issue in history.quality_issues
                    if issue.ingestion_run_id == latest_usable_run.id
                )
                if latest_usable_run is not None
                else ()
            )
            results.append(
                SourceStatus(
                    slug=history.slug,
                    display_name=history.display_name,
                    official_url=history.official_url,
                    terms_url=history.terms_url,
                    attribution_text=history.attribution_text,
                    license_identifier=history.license_identifier,
                    redistribution_status=history.redistribution_status,
                    state=freshness.state,
                    availability="AVAILABLE" if freshness.available else "DATA UNAVAILABLE",
                    has_usable_data=freshness.available,
                    cache_age_seconds=freshness.cache_age_seconds,
                    freshness=freshness.snapshot,
                    latest_run=latest_run,
                    latest_usable_run=latest_usable_run,
                    latest_version=latest_version,
                    quality_issues=usable_quality,
                )
            )
        return results

    def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
        status = next((source for source in self.list_sources() if source.slug == slug), None)
        if status is None:
            return None
        return SourceAvailabilitySnapshot(
            state=cast(
                Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"],
                status.state,
            ),
            has_usable_data=status.has_usable_data,
            cache_age_seconds=status.cache_age_seconds,
        )


class SystemStatusService:
    def __init__(self, database_probe: Callable[[], bool]) -> None:
        self._database_probe = database_probe

    def get_status(self) -> SystemStatus:
        database_available = self._database_probe()
        return SystemStatus(
            service="oceanscope-api",
            version=__version__,
            overall_state="READY" if database_available else "DEGRADED",
            checked_at=datetime.now(UTC),
            database=SystemDependencyStatus(
                state="LIVE" if database_available else "OFFLINE",
                detail=(
                    "Database connectivity verified" if database_available else "DATA UNAVAILABLE"
                ),
            ),
        )
