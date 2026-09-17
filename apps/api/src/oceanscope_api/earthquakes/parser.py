from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from oceanscope_api.earthquakes.contracts import (
    EarthquakeParseResult,
    EarthquakeSchemaError,
    FetchedEarthquakeFeed,
    NormalizedEarthquakeEvent,
)


class UsgsEarthquakeParser:
    normalization_version = "usgs-earthquake-v1"

    def parse(self, dataset: FetchedEarthquakeFeed) -> EarthquakeParseResult:
        try:
            document = json.loads(dataset.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EarthquakeSchemaError("USGS feed is not valid JSON") from error
        if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
            raise EarthquakeSchemaError("USGS feed must be a FeatureCollection")
        features = document.get("features")
        metadata = document.get("metadata")
        if not isinstance(features, list) or not isinstance(metadata, dict):
            raise EarthquakeSchemaError("USGS feed features or metadata are missing")

        quality: Counter[str] = Counter()
        declared_count = metadata.get("count")
        if not isinstance(declared_count, int) or declared_count != len(features):
            quality["provider_revision"] += 1

        records: list[NormalizedEarthquakeEvent] = []
        seen_event_ids: set[str] = set()
        rejected = 0
        for feature in features:
            try:
                record = self._parse_feature(feature)
                if record.event_id in seen_event_ids:
                    raise EarthquakeSchemaError("duplicate: event id")
                seen_event_ids.add(record.event_id)
                records.append(record)
            except EarthquakeSchemaError as error:
                rejected += 1
                quality[_quality_code(error)] += 1
        return EarthquakeParseResult(
            records=records,
            records_received=len(features),
            records_rejected=rejected,
            quality_counts=dict(quality),
        )

    def _parse_feature(self, feature: Any) -> NormalizedEarthquakeEvent:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise EarthquakeSchemaError("missing_required: invalid feature")
        event_id = feature.get("id")
        properties = feature.get("properties")
        geometry = feature.get("geometry")
        if not isinstance(event_id, str) or not event_id.strip():
            raise EarthquakeSchemaError("missing_required: event id")
        if not isinstance(properties, dict) or not isinstance(geometry, dict):
            raise EarthquakeSchemaError("missing_required: properties or geometry")
        coordinates = geometry.get("coordinates")
        if geometry.get("type") != "Point" or not isinstance(coordinates, list):
            raise EarthquakeSchemaError("invalid_coordinate: point geometry")
        if len(coordinates) < 3 or not all(_is_number(value) for value in coordinates[:3]):
            raise EarthquakeSchemaError("invalid_coordinate: coordinate tuple")
        longitude, latitude, depth_km = (float(value) for value in coordinates[:3])
        if not (-180 <= longitude <= 180 and -90 <= latitude <= 90 and -100 <= depth_km <= 1000):
            raise EarthquakeSchemaError("invalid_coordinate: out of range")

        event_time = _milliseconds_timestamp(properties.get("time"))
        updated_at = _milliseconds_timestamp(properties.get("updated"))
        tsunami_value = properties.get("tsunami")
        if (
            not isinstance(tsunami_value, int)
            or isinstance(tsunami_value, bool)
            or tsunami_value not in {0, 1}
        ):
            raise EarthquakeSchemaError("unknown_enum: tsunami")

        magnitude = properties.get("mag")
        if magnitude is not None and (
            not _is_number(magnitude) or not math.isfinite(float(magnitude))
        ):
            raise EarthquakeSchemaError("missing_required: magnitude type")
        significance = properties.get("sig")
        if significance is not None and (
            not isinstance(significance, int) or isinstance(significance, bool) or significance < 0
        ):
            raise EarthquakeSchemaError("missing_required: significance type")

        return NormalizedEarthquakeEvent(
            event_id=event_id.strip(),
            event_time=event_time,
            provider_updated_at=updated_at,
            longitude=longitude,
            latitude=latitude,
            depth_km=depth_km,
            magnitude=float(magnitude) if magnitude is not None else None,
            place=_optional_text(properties.get("place")),
            event_type=_optional_text(properties.get("type")),
            provider_status=_optional_text(properties.get("status")),
            tsunami=bool(tsunami_value),
            significance=significance,
            detail_url=_optional_text(properties.get("detail")),
            quality_flags=[],
            raw_record=feature,
        )


def _milliseconds_timestamp(value: Any) -> datetime:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EarthquakeSchemaError("invalid_timestamp: event timestamp")
    try:
        return datetime.fromtimestamp(value / 1000, tz=UTC)
    except (OverflowError, OSError, ValueError) as error:
        raise EarthquakeSchemaError("invalid_timestamp: event timestamp") from error


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _quality_code(error: EarthquakeSchemaError) -> str:
    prefix = str(error).split(":", 1)[0]
    return (
        prefix
        if prefix
        in {
            "missing_required",
            "invalid_coordinate",
            "invalid_timestamp",
            "unknown_enum",
            "duplicate",
        }
        else "provider_revision"
    )
