from __future__ import annotations

import json
import math
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from oceanscope_api.ocean.contracts import (
    FetchedMarineForecast,
    MarineForecastParseResult,
    MarineSchemaError,
    NormalizedMarineForecastPoint,
)

VALUE_FIELDS = {
    "wave_height": ("wave_height_m", 0.0, 50.0),
    "wave_direction": ("wave_direction_deg", 0.0, 360.0),
    "wave_period": ("wave_period_s", 0.0, 60.0),
    "sea_surface_temperature": ("sea_surface_temperature_c", -5.0, 50.0),
    "ocean_current_velocity": ("ocean_current_velocity_kmh", 0.0, 30.0),
    "ocean_current_direction": ("ocean_current_direction_deg", 0.0, 360.0),
    "sea_level_height_msl": ("sea_level_height_msl_m", -20.0, 20.0),
}

EXPECTED_UNITS = {
    "wave_height": "m",
    "wave_direction": "°",
    "wave_period": "s",
    "sea_surface_temperature": "°C",
    "ocean_current_velocity": "km/h",
    "ocean_current_direction": "°",
    "sea_level_height_msl": "m",
}


class OpenMeteoMarineParser:
    normalization_version = "open-meteo-marine-v1"

    def parse(self, dataset: FetchedMarineForecast) -> MarineForecastParseResult:
        try:
            document = json.loads(dataset.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MarineSchemaError("Open-Meteo response is not valid JSON") from error
        if not isinstance(document, dict):
            raise MarineSchemaError("Open-Meteo response must be an object")
        if document.get("utc_offset_seconds") != 0 or document.get("timezone") != "GMT":
            raise MarineSchemaError("Open-Meteo response is not in requested GMT/UTC")
        grid_latitude = _coordinate(document.get("latitude"), -90, 90, "latitude")
        grid_longitude = _coordinate(document.get("longitude"), -180, 180, "longitude")
        hourly = document.get("hourly")
        units = document.get("hourly_units")
        if not isinstance(hourly, dict) or not isinstance(units, dict):
            raise MarineSchemaError("Open-Meteo hourly values or units are missing")
        times = hourly.get("time")
        if not isinstance(times, list):
            raise MarineSchemaError("Open-Meteo hourly time array is missing")
        if len(times) != dataset.request.forecast_hours:
            raise MarineSchemaError(
                "Open-Meteo hourly time array does not match requested forecast_hours"
            )
        if units.get("time") != "iso8601":
            raise MarineSchemaError("Open-Meteo hourly time unit is not iso8601")
        for variable in dataset.request.variables:
            values = hourly.get(variable)
            unit = units.get(variable)
            if not isinstance(values, list) or len(values) != len(times):
                raise MarineSchemaError(f"Open-Meteo {variable} array is missing or misaligned")
            if unit != EXPECTED_UNITS[variable]:
                raise MarineSchemaError(
                    f"Open-Meteo {variable} unit changed from {EXPECTED_UNITS[variable]}"
                )

        quality: Counter[str] = Counter()
        records: list[NormalizedMarineForecastPoint] = []
        rejected = 0
        previous_time: datetime | None = None
        for index, raw_time in enumerate(times):
            try:
                valid_at = _timestamp(raw_time)
                if previous_time is not None and valid_at <= previous_time:
                    raise MarineSchemaError(
                        "invalid_timestamp: hourly times must be unique and increasing"
                    )
                previous_time = valid_at
                parsed_values: dict[str, float | None] = {
                    target: None for target, _, _ in VALUE_FIELDS.values()
                }
                missing = 0
                raw_record: dict[str, Any] = {"time": raw_time}
                for variable in dataset.request.variables:
                    raw_value = hourly[variable][index]
                    raw_record[variable] = raw_value
                    target, minimum, maximum = VALUE_FIELDS[variable]
                    parsed = _optional_number(raw_value, minimum, maximum, variable)
                    parsed_values[target] = parsed
                    missing += parsed is None
                if missing == len(dataset.request.variables):
                    raise MarineSchemaError("coverage_unknown: all requested values are null")
                flags = ("coverage_unknown",) if missing else ()
                if missing:
                    quality["coverage_unknown"] += 1
                records.append(
                    NormalizedMarineForecastPoint(
                        valid_at=valid_at,
                        requested_latitude=dataset.request.latitude,
                        requested_longitude=dataset.request.longitude,
                        grid_latitude=grid_latitude,
                        grid_longitude=grid_longitude,
                        model=dataset.request.model,
                        units={
                            variable: str(units[variable]) for variable in dataset.request.variables
                        },
                        quality_flags=flags,
                        raw_record=raw_record,
                        **parsed_values,
                    )
                )
            except MarineSchemaError as error:
                rejected += 1
                quality[_quality_code(error)] += 1
        return MarineForecastParseResult(
            records=tuple(records),
            records_received=len(times),
            records_rejected=rejected,
            quality_counts=dict(quality),
        )


def _coordinate(value: Any, minimum: float, maximum: float, name: str) -> float:
    if not _is_number(value) or not minimum <= float(value) <= maximum:
        raise MarineSchemaError(f"invalid_coordinate: grid {name}")
    return float(value)


def _timestamp(value: Any) -> datetime:
    if not isinstance(value, str):
        raise MarineSchemaError("invalid_timestamp: hourly time")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise MarineSchemaError("invalid_timestamp: hourly time") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    if parsed.utcoffset() != UTC.utcoffset(parsed):
        raise MarineSchemaError("invalid_timestamp: hourly time is not UTC")
    return parsed


def _optional_number(value: Any, minimum: float, maximum: float, name: str) -> float | None:
    if value is None:
        return None
    if not _is_number(value) or not math.isfinite(float(value)):
        raise MarineSchemaError(f"out_of_range: {name} is not finite")
    parsed = float(value)
    if not minimum <= parsed <= maximum:
        raise MarineSchemaError(f"out_of_range: {name}")
    return parsed


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _quality_code(error: MarineSchemaError) -> str:
    prefix = str(error).split(":", 1)[0]
    return (
        prefix
        if prefix in {"invalid_timestamp", "out_of_range", "coverage_unknown"}
        else "provider_revision"
    )
