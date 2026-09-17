from __future__ import annotations

import csv
import hashlib
import io
import json
import math
from collections import Counter
from datetime import UTC, datetime
from typing import Any

import zstandard

from oceanscope_api.history.contracts import (
    FetchedHistoricalAisArchive,
    HistoricalAisParseResult,
    HistoricalAisRequest,
    HistoricalAisSchemaError,
    NormalizedHistoricalAisPosition,
)

COLUMN_ALIASES = {
    "MMSI": ("MMSI", "mmsi"),
    "BaseDateTime": ("BaseDateTime", "base_date_time"),
    "LAT": ("LAT", "latitude"),
    "LON": ("LON", "longitude"),
    "SOG": ("SOG", "sog"),
    "COG": ("COG", "cog"),
    "Heading": ("Heading", "heading"),
    "VesselName": ("VesselName", "vessel_name"),
    "IMO": ("IMO", "imo"),
    "CallSign": ("CallSign", "call_sign"),
    "VesselType": ("VesselType", "vessel_type"),
    "Status": ("Status", "status"),
    "Length": ("Length", "length"),
    "Width": ("Width", "width"),
    "Draft": ("Draft", "draft"),
    "Cargo": ("Cargo", "cargo"),
    "TransceiverClass": ("TransceiverClass", "transceiver"),
}
REQUIRED_COLUMNS = frozenset(COLUMN_ALIASES) - {"TransceiverClass"}
MAX_ROWS_SCANNED = 50_000_000


class MarineCadastreCsvParser:
    normalization_version = "marinecadastre-csv-v1"

    def parse(self, archive: FetchedHistoricalAisArchive) -> HistoricalAisParseResult:
        records: list[NormalizedHistoricalAisPosition] = []
        quality: Counter[str] = Counter()
        seen: set[str] = set()
        received = rejected = filtered = duplicate = capped = 0
        try:
            with (
                archive.archive_path.open("rb") as compressed,
                zstandard.ZstdDecompressor().stream_reader(
                    compressed, read_across_frames=True
                ) as decompressed,
                io.TextIOWrapper(decompressed, encoding="utf-8-sig", newline="") as text,
            ):
                reader = csv.DictReader(text)
                source_columns = set(reader.fieldnames or ())
                resolved_columns = {
                    canonical: next((alias for alias in aliases if alias in source_columns), None)
                    for canonical, aliases in COLUMN_ALIASES.items()
                }
                missing = sorted(
                    name for name in REQUIRED_COLUMNS if resolved_columns[name] is None
                )
                if missing:
                    raise HistoricalAisSchemaError(
                        f"MarineCadastre archive is missing columns: {', '.join(missing)}"
                    )
                for row in reader:
                    received += 1
                    if received > MAX_ROWS_SCANNED:
                        raise HistoricalAisSchemaError(
                            f"MarineCadastre archive exceeds {MAX_ROWS_SCANNED} rows"
                        )
                    try:
                        observed_at = _timestamp(
                            _value(row, resolved_columns, "BaseDateTime"), archive.request
                        )
                        latitude = _coordinate(
                            _value(row, resolved_columns, "LAT"), -90, 90, "latitude"
                        )
                        longitude = _coordinate(
                            _value(row, resolved_columns, "LON"), -180, 180, "longitude"
                        )
                    except HistoricalAisSchemaError as error:
                        rejected += 1
                        quality[_quality_code(error)] += 1
                        continue
                    if not _within_request(archive.request, observed_at, longitude, latitude):
                        filtered += 1
                        continue
                    try:
                        mmsi = _mmsi(_value(row, resolved_columns, "MMSI"))
                        record, flags = _normalize_row(
                            archive,
                            row,
                            resolved_columns,
                            mmsi,
                            observed_at,
                            longitude,
                            latitude,
                        )
                    except HistoricalAisSchemaError as error:
                        rejected += 1
                        quality[_quality_code(error)] += 1
                        continue
                    if record.record_fingerprint in seen:
                        duplicate += 1
                        quality["duplicate"] += 1
                        continue
                    seen.add(record.record_fingerprint)
                    if len(records) >= archive.request.record_limit:
                        capped += 1
                        continue
                    for flag in flags:
                        quality[flag] += 1
                    records.append(record)
        except HistoricalAisSchemaError:
            raise
        except (OSError, UnicodeError, csv.Error, zstandard.ZstdError) as error:
            raise HistoricalAisSchemaError(
                f"MarineCadastre archive could not be decoded: {error}"
            ) from error
        if capped:
            quality["coverage_unknown"] += capped
        return HistoricalAisParseResult(
            records=tuple(records),
            records_received=received,
            records_rejected=rejected,
            records_filtered=filtered,
            records_duplicate=duplicate,
            records_capped=capped,
            quality_counts=dict(quality),
        )


def _normalize_row(
    archive: FetchedHistoricalAisArchive,
    row: dict[str, str | None],
    columns: dict[str, str | None],
    mmsi: str,
    observed_at: datetime,
    longitude: float,
    latitude: float,
) -> tuple[NormalizedHistoricalAisPosition, tuple[str, ...]]:
    flags: set[str] = set()
    sog = _optional_float(_value(row, columns, "SOG"), 0, 102.2, sentinels={102.3}, flags=flags)
    cog = _optional_float(_value(row, columns, "COG"), 0, 359.9, sentinels={360.0}, flags=flags)
    heading = _optional_float(
        _value(row, columns, "Heading"), 0, 359, sentinels={511.0}, flags=flags
    )
    vessel_type = _optional_int(_value(row, columns, "VesselType"), 0, 9999, flags)
    status = _optional_int(_value(row, columns, "Status"), 0, 15, flags)
    length = _optional_float(_value(row, columns, "Length"), 0, 500, flags=flags)
    width = _optional_float(_value(row, columns, "Width"), 0, 100, flags=flags)
    draft = _optional_float(_value(row, columns, "Draft"), 0, 30, flags=flags)
    raw_record = dict(row)
    fingerprint = hashlib.sha256(
        json.dumps(raw_record, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    record = NormalizedHistoricalAisPosition(
        record_fingerprint=fingerprint,
        archive_date=archive.request.archive_date,
        mmsi=mmsi,
        observed_at=observed_at,
        longitude=longitude,
        latitude=latitude,
        sog_knots=sog,
        cog_deg=cog,
        heading_deg=heading,
        vessel_name=_optional_text(_value(row, columns, "VesselName"), 200, flags),
        imo=_optional_text(_value(row, columns, "IMO"), 30, flags),
        call_sign=_optional_text(_value(row, columns, "CallSign"), 50, flags),
        vessel_type=vessel_type,
        navigation_status=status,
        length_m=length,
        width_m=width,
        draft_m=draft,
        cargo=_optional_text(_value(row, columns, "Cargo"), 100, flags),
        transceiver_class=_optional_text(_value(row, columns, "TransceiverClass"), 20, flags),
        quality_flags=tuple(sorted(flags)),
        raw_record=raw_record,
    )
    return record, record.quality_flags


def _value(
    row: dict[str, str | None], columns: dict[str, str | None], canonical: str
) -> str | None:
    source_name = columns.get(canonical)
    return row.get(source_name) if source_name is not None else None


def _within_request(
    request: HistoricalAisRequest,
    observed_at: datetime,
    longitude: float,
    latitude: float,
) -> bool:
    return (
        request.start_at.astimezone(UTC) <= observed_at < request.end_at.astimezone(UTC)
        and request.min_longitude <= longitude <= request.max_longitude
        and request.min_latitude <= latitude <= request.max_latitude
    )


def _timestamp(value: Any, request: HistoricalAisRequest) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise HistoricalAisSchemaError("missing_required: BaseDateTime")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise HistoricalAisSchemaError("invalid_timestamp: BaseDateTime") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    parsed = parsed.astimezone(UTC)
    if parsed.date() != request.archive_date:
        raise HistoricalAisSchemaError("invalid_timestamp: outside archive date")
    return parsed


def _coordinate(value: Any, minimum: float, maximum: float, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise HistoricalAisSchemaError(f"invalid_coordinate: {name}") from error
    if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
        raise HistoricalAisSchemaError(f"invalid_coordinate: {name}")
    return parsed


def _mmsi(value: Any) -> str:
    text = str(value or "").strip()
    if len(text) != 9 or not text.isascii() or not text.isdigit():
        raise HistoricalAisSchemaError("missing_required: valid nine-digit MMSI")
    return text


def _optional_float(
    value: Any,
    minimum: float,
    maximum: float,
    *,
    sentinels: set[float] | None = None,
    flags: set[str],
) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        flags.add("out_of_range")
        return None
    if sentinels and parsed in sentinels:
        return None
    if not math.isfinite(parsed) or not minimum <= parsed <= maximum:
        flags.add("out_of_range")
        return None
    return parsed


def _optional_int(value: Any, minimum: int, maximum: int, flags: set[str]) -> int | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = int(text)
    except ValueError:
        flags.add("unknown_enum")
        return None
    if not minimum <= parsed <= maximum:
        flags.add("unknown_enum")
        return None
    return parsed


def _optional_text(value: Any, maximum: int, flags: set[str]) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    if len(text) > maximum:
        flags.add("out_of_range")
        return None
    return text


def _quality_code(error: HistoricalAisSchemaError) -> str:
    prefix = str(error).split(":", 1)[0]
    return (
        prefix
        if prefix in {"missing_required", "invalid_coordinate", "invalid_timestamp"}
        else "provider_revision"
    )
