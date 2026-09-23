"""Offline normalization of Pelyr v1 position frames.

This module deliberately has no transport or credential concerns.  It accepts one
provider frame and the source directory captured for that connection, then emits the
existing provider-neutral ``LiveAisPosition`` contract.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from oceanscope_api.api.contracts.live_ais import LiveAisPosition, LiveAisProvenance

PELYR_STREAM_URL: Final = "wss://stream.pelyr.com/v1/stream"
PELYR_SOURCE_SLUG: Final = "pelyr-open-ais"
PELYR_SCHEMA_VERSION: Final = "pelyr-v1-position-normalizer-v1"


class PelyrNormalizationError(ValueError):
    """Raised when a Pelyr frame cannot be published as a normalized position."""


@dataclass(frozen=True, slots=True)
class PelyrSourceDescriptor:
    """The licence and attribution metadata for one Pelyr source id."""

    source_id: int
    license_identifier: str
    attribution_text: str

    @classmethod
    def from_provider_entry(cls, entry: Mapping[str, object]) -> PelyrSourceDescriptor:
        source_id = _required_int(entry, "id")
        license_identifier = _required_text(entry, "license")
        attribution = entry.get("attribution")
        if not isinstance(attribution, str):
            raise PelyrNormalizationError("attribution must be text")
        attribution_text = attribution
        return cls(source_id, license_identifier, attribution_text)

    def validate_publishable(self) -> None:
        if self.source_id == 0:
            raise PelyrNormalizationError("Pelyr source 0 has NOASSERTION and cannot be published")
        if self.license_identifier.strip().upper() == "NOASSERTION":
            raise PelyrNormalizationError(
                f"Pelyr source {self.source_id} has NOASSERTION and cannot be published"
            )
        if not self.attribution_text.strip():
            raise PelyrNormalizationError(f"Pelyr source {self.source_id} has empty attribution")


class PelyrSourceDirectory:
    """Immutable lookup table built from one connection's ``welcome.sources``."""

    def __init__(self, entries: Iterable[PelyrSourceDescriptor]) -> None:
        descriptors = tuple(entries)
        by_id: dict[int, PelyrSourceDescriptor] = {}
        for descriptor in descriptors:
            if descriptor.source_id in by_id:
                raise PelyrNormalizationError(f"duplicate Pelyr source id {descriptor.source_id}")
            by_id[descriptor.source_id] = descriptor
        self._by_id = by_id

    @classmethod
    def from_provider_entries(cls, entries: Iterable[Mapping[str, object]]) -> PelyrSourceDirectory:
        return cls(PelyrSourceDescriptor.from_provider_entry(entry) for entry in entries)

    def resolve(self, source_id: object) -> PelyrSourceDescriptor:
        normalized_id = _required_int_value(source_id, "license")
        try:
            descriptor = self._by_id[normalized_id]
        except KeyError as error:
            raise PelyrNormalizationError(
                f"unknown Pelyr license source id {normalized_id}"
            ) from error
        descriptor.validate_publishable()
        return descriptor


class PelyrPositionNormalizer:
    """Map one Pelyr ``position`` frame to the public Live AIS position contract."""

    def normalize(
        self,
        frame: Mapping[str, object],
        source_directory: PelyrSourceDirectory,
        *,
        ingested_at: datetime,
        normalized_at: datetime,
    ) -> LiveAisPosition:
        frame_type = _required_text(frame, "type")
        if frame_type != "position":
            raise PelyrNormalizationError("Pelyr frame type must be position")
        source = source_directory.resolve(frame.get("license"))
        frame_id = _required_identifier(frame.get("id"), "id")
        data = frame.get("data")
        if not isinstance(data, Mapping):
            raise PelyrNormalizationError("data is required and must be an object")
        mmsi = _required_mmsi(data.get("mmsi"))

        msg_type = _required_identifier(data.get("msg_type"), "msg_type")
        observed_at = _utc_datetime(data.get("rx_ts"), "rx_ts")
        ingested_at_utc = _utc_datetime(ingested_at, "ingested_at")
        normalized_at_utc = _utc_datetime(normalized_at, "normalized_at")

        latitude = _bounded_number(data.get("lat"), "lat", minimum=-90, maximum=90)
        longitude = _bounded_number(data.get("lon"), "lon", minimum=-180, maximum=180)
        speed = _optional_bounded_number(
            data.get("sog"), "sog", minimum=0, maximum=102.3, maximum_inclusive=False
        )
        course = _optional_bounded_number(
            data.get("cog"), "cog", minimum=0, maximum=360, maximum_inclusive=False
        )
        heading = _optional_bounded_int(
            data.get("heading"), "heading", minimum=0, maximum=360, maximum_inclusive=False
        )

        return LiveAisPosition(
            observation_id=f"pelyr:{source.source_id}:{frame_id}",
            mmsi=mmsi,
            observed_at=observed_at,
            longitude=longitude,
            latitude=latitude,
            speed_over_ground_knots=speed,
            course_over_ground_deg=course,
            true_heading_deg=heading,
            navigational_status_code=None,
            quality_flags=(),
            provenance=LiveAisProvenance(
                source_slug=PELYR_SOURCE_SLUG,
                source_url=PELYR_STREAM_URL,
                attribution_text=source.attribution_text,
                # The connection source id and licence are part of the versioned
                # provenance value because the frozen v1 public model has no
                # provider-specific licence columns.
                data_version=f"pelyr-v1/source-{source.source_id}/{source.license_identifier}",
                schema_version=PELYR_SCHEMA_VERSION,
                provider_message_type=msg_type,
                source_event_id=frame_id,
                ingested_at=ingested_at_utc,
                normalized_at=normalized_at_utc,
                source_state="LIVE",
                cache_age_seconds=None,
            ),
        )


def _required_text(value: Mapping[str, object], key: str) -> str:
    return _required_text_value(value.get(key), key)


def _required_text_value(value: object, key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PelyrNormalizationError(f"{key} is required and must be non-empty text")
    return value


def _required_identifier(value: object, key: str) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise PelyrNormalizationError(f"{key} is required and must be text or an integer")
    identifier = str(value)
    if not identifier.strip():
        raise PelyrNormalizationError(f"{key} is required and must be non-empty")
    return identifier


def _required_mmsi(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise PelyrNormalizationError("mmsi is required and must be a nine-digit value")
    mmsi = str(value)
    if len(mmsi) != 9 or not mmsi.isdecimal():
        raise PelyrNormalizationError("mmsi must be a nine-digit value")
    return mmsi


def _required_int(value: Mapping[str, object], key: str) -> int:
    return _required_int_value(value.get(key), key)


def _required_int_value(value: object, key: str) -> int:
    if isinstance(value, bool):
        raise PelyrNormalizationError(f"{key} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise PelyrNormalizationError(f"{key} must be an integer")


def _number(value: object, key: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PelyrNormalizationError(f"{key} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise PelyrNormalizationError(f"{key} must be a finite number")
    return number


def _bounded_number(value: object, key: str, *, minimum: float, maximum: float) -> float:
    number = _number(value, key)
    if number < minimum or number > maximum:
        raise PelyrNormalizationError(f"{key} is outside [{minimum}, {maximum}]")
    return number


def _optional_bounded_number(
    value: object,
    key: str,
    *,
    minimum: float,
    maximum: float,
    maximum_inclusive: bool,
) -> float | None:
    if value is None:
        return None
    number = _number(value, key)
    if number < minimum or (number >= maximum if not maximum_inclusive else number > maximum):
        upper = "<" if not maximum_inclusive else "<="
        raise PelyrNormalizationError(f"{key} must be in [{minimum}, {upper}{maximum}")
    return number


def _optional_bounded_int(
    value: object,
    key: str,
    *,
    minimum: int,
    maximum: int,
    maximum_inclusive: bool,
) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise PelyrNormalizationError(f"{key} must be an integer or null")
    if value < minimum or (value >= maximum if not maximum_inclusive else value > maximum):
        upper = "<" if not maximum_inclusive else "<="
        raise PelyrNormalizationError(f"{key} must be in [{minimum}, {upper}{maximum}")
    return value


def _utc_datetime(value: object, key: str) -> datetime:
    if isinstance(value, str):
        candidate = value.replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError as error:
            raise PelyrNormalizationError(f"{key} must be a valid ISO-8601 timestamp") from error
    elif isinstance(value, datetime):
        parsed = value
    else:
        raise PelyrNormalizationError(f"{key} must be a timezone-aware timestamp")
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PelyrNormalizationError(f"{key} must be timezone-aware")
    return parsed.astimezone(UTC)
