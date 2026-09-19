from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

LIVE_AIS_PROTOCOL_VERSION: Literal["1.0"] = "1.0"

SourceState = Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
Availability = Literal["AVAILABLE", "DATA UNAVAILABLE"]
CoverageState = Literal["COVERED", "NO COVERAGE"]
ConnectionState = Literal["CONNECTING", "CONNECTED", "RECONNECTING", "DISCONNECTED"]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LiveAisBounds(ContractModel):
    west: float = Field(ge=-180, le=180)
    south: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)

    @model_validator(mode="after")
    def validate_ordered_bounds(self) -> LiveAisBounds:
        if self.west >= self.east:
            raise ValueError(
                "west must be less than east; antimeridian bounds are not supported in v1"
            )
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        return self


class LiveAisCoverage(ContractModel):
    state: CoverageState
    description: str = Field(min_length=1, max_length=500)
    bounds: LiveAisBounds | None
    effective_at: datetime

    @field_validator("effective_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("effective_at must be timezone-aware")
        return value

    @model_validator(mode="after")
    def require_bounds_for_covered_state(self) -> LiveAisCoverage:
        if self.state == "COVERED" and self.bounds is None:
            raise ValueError("covered live AIS requires explicit bounds")
        return self


class LiveAisProvenance(ContractModel):
    source_slug: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1)
    attribution_text: str = Field(min_length=1)
    data_version: str = Field(min_length=1, max_length=100)
    schema_version: str = Field(min_length=1, max_length=100)
    provider_message_type: str = Field(min_length=1, max_length=100)
    source_event_id: str | None = Field(default=None, max_length=200)
    ingested_at: datetime
    normalized_at: datetime
    source_state: SourceState
    cache_age_seconds: int | None = Field(default=None, ge=0)

    @field_validator("ingested_at", "normalized_at")
    @classmethod
    def require_aware_times(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("live AIS timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_cache_and_processing_time(self) -> LiveAisProvenance:
        if (self.source_state == "CACHED") != (self.cache_age_seconds is not None):
            raise ValueError("cache_age_seconds is required only when source_state is CACHED")
        if self.normalized_at < self.ingested_at:
            raise ValueError("normalized_at cannot precede ingested_at")
        return self


class LiveAisPosition(ContractModel):
    observation_id: str = Field(min_length=1, max_length=200)
    mmsi: str = Field(pattern=r"^\d{9}$")
    observed_at: datetime
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    speed_over_ground_knots: float | None = Field(default=None, ge=0, lt=102.3)
    course_over_ground_deg: float | None = Field(default=None, ge=0, lt=360)
    true_heading_deg: int | None = Field(default=None, ge=0, lt=360)
    navigational_status_code: int | None = Field(default=None, ge=0, le=15)
    quality_flags: tuple[str, ...] = ()
    provenance: LiveAisProvenance

    @field_validator("observed_at")
    @classmethod
    def require_aware_observed_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must be timezone-aware")
        return value


class LiveAisEventBase(ContractModel):
    protocol_version: Literal["1.0"] = LIVE_AIS_PROTOCOL_VERSION
    stream_epoch: UUID
    sequence: int = Field(ge=0)
    emitted_at: datetime

    @field_validator("emitted_at")
    @classmethod
    def require_aware_emitted_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("emitted_at must be timezone-aware")
        return value


class LiveAisSnapshotEvent(LiveAisEventBase):
    event: Literal["vessel.snapshot"]
    availability: Availability
    source_state: SourceState
    cache_age_seconds: int | None = Field(default=None, ge=0)
    coverage: LiveAisCoverage
    positions: tuple[LiveAisPosition, ...]
    truncated: bool

    @model_validator(mode="after")
    def prevent_unavailable_payload(self) -> LiveAisSnapshotEvent:
        if self.availability == "DATA UNAVAILABLE" and self.positions:
            raise ValueError("unavailable snapshots cannot carry vessel positions")
        if self.coverage.state == "NO COVERAGE" and self.positions:
            raise ValueError("no-coverage snapshots cannot carry vessel positions")
        if (self.source_state == "CACHED") != (self.cache_age_seconds is not None):
            raise ValueError("cache_age_seconds is required only when source_state is CACHED")
        return self


class LiveAisPositionEvent(LiveAisEventBase):
    event: Literal["vessel.position"]
    position: LiveAisPosition


class LiveAisStatusEvent(LiveAisEventBase):
    event: Literal["stream.status"]
    connection_state: ConnectionState
    source_state: SourceState
    cache_age_seconds: int | None = Field(default=None, ge=0)
    availability: Availability
    coverage: LiveAisCoverage
    last_observation_at: datetime | None
    retry_at: datetime | None
    detail: str = Field(min_length=1, max_length=500)

    @field_validator("last_observation_at", "retry_at")
    @classmethod
    def require_aware_optional_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("stream status timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_cache_age(self) -> LiveAisStatusEvent:
        if (self.source_state == "CACHED") != (self.cache_age_seconds is not None):
            raise ValueError("cache_age_seconds is required only when source_state is CACHED")
        return self


class LiveAisGapEvent(LiveAisEventBase):
    event: Literal["stream.gap"]
    gap_started_at: datetime
    gap_ended_at: datetime | None
    reason: Literal[
        "provider_disconnect",
        "server_backpressure",
        "client_backpressure",
        "subscription_change",
    ]
    dropped_updates: int | None = Field(default=None, ge=0)
    replay_available: Literal[False] = False
    detail: str = Field(min_length=1, max_length=500)

    @field_validator("gap_started_at", "gap_ended_at")
    @classmethod
    def require_aware_gap_times(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("gap timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_gap_window(self) -> LiveAisGapEvent:
        if self.gap_ended_at is not None and self.gap_ended_at < self.gap_started_at:
            raise ValueError("gap_ended_at cannot precede gap_started_at")
        return self


LiveAisServerEvent = Annotated[
    LiveAisSnapshotEvent | LiveAisPositionEvent | LiveAisStatusEvent | LiveAisGapEvent,
    Field(discriminator="event"),
]

live_ais_server_event_adapter: TypeAdapter[LiveAisServerEvent] = TypeAdapter(LiveAisServerEvent)
