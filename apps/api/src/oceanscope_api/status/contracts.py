from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol
from uuid import UUID


@dataclass(frozen=True)
class SourceVersionSnapshot:
    id: UUID
    data_version: str
    schema_version: str
    source_url: str
    published_at: datetime | None
    retrieved_at: datetime


@dataclass(frozen=True)
class IngestionRunSnapshot:
    id: UUID
    source_version_id: UUID | None
    status: str
    source_state: str
    cache_age_seconds: int | None
    started_at: datetime
    finished_at: datetime | None
    records_received: int
    records_accepted: int
    records_rejected: int


@dataclass(frozen=True)
class QualityIssueSnapshot:
    ingestion_run_id: UUID
    code: str
    severity: str
    record_count: int
    message: str


@dataclass(frozen=True)
class SourceHistory:
    slug: str
    display_name: str
    official_url: str
    terms_url: str | None
    attribution_text: str
    license_identifier: str | None
    redistribution_status: str
    versions: tuple[SourceVersionSnapshot, ...]
    runs: tuple[IngestionRunSnapshot, ...]
    quality_issues: tuple[QualityIssueSnapshot, ...]


class SourceStatusRepository(Protocol):
    def list_source_histories(self) -> list[SourceHistory]: ...


@dataclass(frozen=True)
class FreshnessSnapshot:
    age_seconds: int | None
    live_ttl_seconds: int
    delayed_ttl_seconds: int
    cache_ttl_seconds: int | None


@dataclass(frozen=True)
class SourceStatus:
    slug: str
    display_name: str
    official_url: str
    terms_url: str | None
    attribution_text: str
    license_identifier: str | None
    redistribution_status: str
    state: str
    availability: str
    has_usable_data: bool
    cache_age_seconds: int | None
    freshness: FreshnessSnapshot
    latest_run: IngestionRunSnapshot | None
    latest_usable_run: IngestionRunSnapshot | None
    latest_version: SourceVersionSnapshot | None
    quality_issues: tuple[QualityIssueSnapshot, ...]


@dataclass(frozen=True)
class SourceAvailabilitySnapshot:
    state: Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
    has_usable_data: bool
    cache_age_seconds: int | None


class SourceAvailabilityLookup(Protocol):
    def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None: ...


@dataclass(frozen=True)
class SystemDependencyStatus:
    state: Literal["LIVE", "OFFLINE"]
    detail: str


@dataclass(frozen=True)
class SystemStatus:
    service: Literal["oceanscope-api"]
    version: str
    overall_state: Literal["READY", "DEGRADED"]
    checked_at: datetime
    database: SystemDependencyStatus
