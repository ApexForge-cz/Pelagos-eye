from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Protocol
from uuid import UUID

from oceanscope_api.ports.contracts import SourceDescriptor

MARINE_VARIABLES = (
    "wave_height",
    "wave_direction",
    "wave_period",
    "sea_surface_temperature",
    "ocean_current_velocity",
    "ocean_current_direction",
    "sea_level_height_msl",
)


class MarineDataError(RuntimeError):
    """Base error for marine forecast acquisition and parsing."""


class MarineDownloadError(MarineDataError):
    """Raised when the official forecast cannot be downloaded safely."""


class MarineSchemaError(MarineDataError):
    """Raised when a provider response violates the expected contract."""


@dataclass(frozen=True)
class MarineForecastRequest:
    latitude: float
    longitude: float
    forecast_hours: int = 24
    model: str = "best_match"
    variables: tuple[str, ...] = MARINE_VARIABLES

    def __post_init__(self) -> None:
        if not -90 <= self.latitude <= 90:
            raise ValueError("latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValueError("longitude must be between -180 and 180")
        if not 1 <= self.forecast_hours <= 168:
            raise ValueError("forecast_hours must be between 1 and 168")
        if self.model != "best_match":
            raise ValueError("only the verified best_match model is supported")
        if not self.variables or any(
            variable not in MARINE_VARIABLES for variable in self.variables
        ):
            raise ValueError("request contains an unsupported marine variable")
        if len(set(self.variables)) != len(self.variables):
            raise ValueError("marine variables must be unique")

    @property
    def request_key(self) -> str:
        canonical = json.dumps(
            {
                "forecast_hours": self.forecast_hours,
                "latitude": round(self.latitude, 6),
                "longitude": round(self.longitude, 6),
                "model": self.model,
                "variables": self.variables,
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True)
class FetchedMarineForecast:
    source: SourceDescriptor
    request: MarineForecastRequest
    data_version: str
    schema_version: str
    source_url: str
    content: bytes
    checksum_sha256: str
    retrieved_at: datetime


@dataclass(frozen=True)
class NormalizedMarineForecastPoint:
    valid_at: datetime
    requested_latitude: float
    requested_longitude: float
    grid_latitude: float
    grid_longitude: float
    model: str
    wave_height_m: float | None
    wave_direction_deg: float | None
    wave_period_s: float | None
    sea_surface_temperature_c: float | None
    ocean_current_velocity_kmh: float | None
    ocean_current_direction_deg: float | None
    sea_level_height_msl_m: float | None
    units: dict[str, str]
    quality_flags: tuple[str, ...] = ()
    raw_record: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarineForecastParseResult:
    records: tuple[NormalizedMarineForecastPoint, ...]
    records_received: int
    records_rejected: int
    quality_counts: dict[str, int]


class MarineForecastProvider(Protocol):
    source: SourceDescriptor

    def fetch(self, request: MarineForecastRequest) -> FetchedMarineForecast: ...


class MarineForecastParser(Protocol):
    normalization_version: str

    def parse(self, dataset: FetchedMarineForecast) -> MarineForecastParseResult: ...


@dataclass(frozen=True)
class MarineForecastQuery:
    latitude: float
    longitude: float
    start_at: datetime
    end_at: datetime
    limit: int = 168
    offset: int = 0


@dataclass(frozen=True)
class MarineForecastRecord:
    id: UUID
    requested_latitude: float
    requested_longitude: float
    grid_latitude: float
    grid_longitude: float
    valid_at: datetime
    model: str
    wave_height_m: float | None
    wave_direction_deg: float | None
    wave_period_s: float | None
    sea_surface_temperature_c: float | None
    ocean_current_velocity_kmh: float | None
    ocean_current_direction_deg: float | None
    sea_level_height_msl_m: float | None
    units: dict[str, str]
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
class MarineForecastQueryResult:
    records: tuple[MarineForecastRecord, ...]
    total: int


class MarineForecastQueryRepository(Protocol):
    def query(self, query: MarineForecastQuery) -> MarineForecastQueryResult: ...
