from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from oceanscope_api.ports.contracts import SourceDescriptor


class EarthquakeDataError(RuntimeError):
    pass


class EarthquakeSchemaError(EarthquakeDataError):
    pass


@dataclass(frozen=True)
class FetchedEarthquakeFeed:
    source: SourceDescriptor
    data_version: str
    schema_version: str
    source_url: str
    content: bytes
    checksum_sha256: str
    generated_at: datetime
    retrieved_at: datetime


@dataclass(frozen=True)
class NormalizedEarthquakeEvent:
    event_id: str
    event_time: datetime
    provider_updated_at: datetime
    longitude: float
    latitude: float
    depth_km: float
    magnitude: float | None
    place: str | None
    event_type: str | None
    provider_status: str | None
    tsunami: bool
    significance: int | None
    detail_url: str | None
    quality_flags: list[str]
    raw_record: dict[str, Any]


@dataclass(frozen=True)
class EarthquakeParseResult:
    records: list[NormalizedEarthquakeEvent]
    records_received: int
    records_rejected: int
    quality_counts: dict[str, int]


class EarthquakeFeedProvider(Protocol):
    source: SourceDescriptor

    def fetch(self) -> FetchedEarthquakeFeed: ...


class EarthquakeFeedParser(Protocol):
    normalization_version: str

    def parse(self, dataset: FetchedEarthquakeFeed) -> EarthquakeParseResult: ...


@dataclass(frozen=True)
class EarthquakeSearchQuery:
    start_at: datetime
    end_at: datetime
    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float
    min_magnitude: float | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True)
class EarthquakeSearchRecord:
    id: UUID
    event_id: str
    event_time: datetime
    provider_updated_at: datetime
    longitude: float
    latitude: float
    depth_km: float
    magnitude: float | None
    place: str | None
    event_type: str | None
    provider_status: str | None
    tsunami: bool
    significance: int | None
    detail_url: str | None
    quality_flags: tuple[str, ...]
    normalized_at: datetime
    source_slug: str
    source_display_name: str
    source_url: str
    attribution_text: str
    data_version: str
    schema_version: str
    published_at: datetime | None
    retrieved_at: datetime
    ingested_at: datetime
    source_state: Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
    cache_age_seconds: int | None


@dataclass(frozen=True)
class EarthquakeSearchResult:
    records: tuple[EarthquakeSearchRecord, ...]
    total: int


class EarthquakeSearchRepository(Protocol):
    def search(self, query: EarthquakeSearchQuery) -> EarthquakeSearchResult: ...
