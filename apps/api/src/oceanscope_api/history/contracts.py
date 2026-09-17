from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from oceanscope_api.ports.contracts import SourceDescriptor
from oceanscope_api.provenance.models import SourceState


class HistoricalAisError(RuntimeError):
    """Base error for historical AIS acquisition and parsing."""


class HistoricalAisDownloadError(HistoricalAisError):
    """Raised when an official archive cannot be downloaded safely."""


class HistoricalAisSchemaError(HistoricalAisError):
    """Raised when an official archive violates the supported schema."""


@dataclass(frozen=True)
class HistoricalAisRequest:
    archive_date: date
    min_longitude: float
    min_latitude: float
    max_longitude: float
    max_latitude: float
    start_at: datetime
    end_at: datetime
    record_limit: int = 5_000

    def __post_init__(self) -> None:
        coordinates = (
            self.min_longitude,
            self.min_latitude,
            self.max_longitude,
            self.max_latitude,
        )
        if not all(math.isfinite(value) for value in coordinates):
            raise ValueError("bounding-box coordinates must be finite")
        if not -180 <= self.min_longitude < self.max_longitude <= 180:
            raise ValueError("longitude bounds must be ordered within WGS 84")
        if not -90 <= self.min_latitude < self.max_latitude <= 90:
            raise ValueError("latitude bounds must be ordered within WGS 84")
        if self.max_longitude - self.min_longitude > 5:
            raise ValueError("longitude span cannot exceed 5 degrees")
        if self.max_latitude - self.min_latitude > 5:
            raise ValueError("latitude span cannot exceed 5 degrees")
        if not 2015 <= self.archive_date.year <= 2025:
            raise ValueError("only the verified 2015-2025 CSV schema is supported")
        if self.start_at.tzinfo is None or self.end_at.tzinfo is None:
            raise ValueError("time bounds must be timezone-aware")
        start_at = self.start_at.astimezone(UTC)
        end_at = self.end_at.astimezone(UTC)
        day_start = datetime.combine(self.archive_date, datetime.min.time(), tzinfo=UTC)
        if not day_start <= start_at < end_at <= day_start + timedelta(days=1):
            raise ValueError("time bounds must be within the selected UTC archive date")
        if end_at - start_at > timedelta(hours=6):
            raise ValueError("time window cannot exceed 6 hours")
        if not 1 <= self.record_limit <= 100_000:
            raise ValueError("record_limit must be between 1 and 100000")

    @property
    def request_key(self) -> str:
        canonical = json.dumps(
            {
                "archive_date": self.archive_date.isoformat(),
                "bounds": [
                    round(self.min_longitude, 6),
                    round(self.min_latitude, 6),
                    round(self.max_longitude, 6),
                    round(self.max_latitude, 6),
                ],
                "end_at": self.end_at.astimezone(UTC).isoformat(),
                "record_limit": self.record_limit,
                "start_at": self.start_at.astimezone(UTC).isoformat(),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class FetchedHistoricalAisArchive:
    source: SourceDescriptor
    request: HistoricalAisRequest
    data_version: str
    schema_version: str
    source_url: str
    archive_path: Path
    checksum_sha256: str
    size_bytes: int
    retrieved_at: datetime
    source_state: SourceState = SourceState.LIVE
    cache_age_seconds: int | None = None


@dataclass(frozen=True)
class NormalizedHistoricalAisPosition:
    record_fingerprint: str
    archive_date: date
    mmsi: str
    observed_at: datetime
    longitude: float
    latitude: float
    sog_knots: float | None
    cog_deg: float | None
    heading_deg: float | None
    vessel_name: str | None
    imo: str | None
    call_sign: str | None
    vessel_type: int | None
    navigation_status: int | None
    length_m: float | None
    width_m: float | None
    draft_m: float | None
    cargo: str | None
    transceiver_class: str | None
    quality_flags: tuple[str, ...] = ()
    raw_record: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HistoricalAisParseResult:
    records: tuple[NormalizedHistoricalAisPosition, ...]
    records_received: int
    records_rejected: int
    records_filtered: int
    records_duplicate: int
    records_capped: int
    quality_counts: dict[str, int]


class HistoricalAisProvider(Protocol):
    source: SourceDescriptor

    def fetch(self, request: HistoricalAisRequest) -> FetchedHistoricalAisArchive: ...


class HistoricalAisParser(Protocol):
    normalization_version: str

    def parse(self, archive: FetchedHistoricalAisArchive) -> HistoricalAisParseResult: ...
