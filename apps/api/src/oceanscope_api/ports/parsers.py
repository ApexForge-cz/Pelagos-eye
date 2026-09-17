from __future__ import annotations

import csv
import hashlib
import io
import re
from collections import Counter
from collections.abc import Iterable
from zipfile import BadZipFile, ZipFile

from oceanscope_api.ports.contracts import (
    FetchedPortDataset,
    NormalizedPortSourceRecord,
    PortParseResult,
    PortSchemaError,
)

UNLOCODE_COLUMNS = (
    "change",
    "country",
    "location",
    "name",
    "name_without_diacritics",
    "subdivision",
    "function",
    "status",
    "date",
    "iata",
    "coordinates",
    "remarks",
)
UNLOCODE_FILE_PATTERN = re.compile(r"(?:^|/)UNLOCODE CodeListPart\d+\.csv$")
UNLOCODE_CODE_PATTERN = re.compile(r"^[A-Z]{2}[A-Z2-9]{3}$")
UNLOCODE_COORDINATE_PATTERN = re.compile(r"^(\d{2})(\d{2})([NS])\s+(\d{3})(\d{2})([EW])$")
WPI_COORDINATE_PATTERN = re.compile(r"^(\d{1,3})°(\d{1,2})'(\d{1,2}(?:\.\d+)?)\"([NSEW])$")
WPI_REQUIRED_COLUMNS = {
    "portNumber",
    "portName",
    "countryCode",
    "latitude",
    "longitude",
    "unloCode",
}


class UnLocodeParser:
    normalization_version = "unlocode-port-normalizer-v1"

    def parse(self, dataset: FetchedPortDataset) -> PortParseResult:
        records: list[NormalizedPortSourceRecord] = []
        issues: Counter[str] = Counter()
        received = 0
        rejected = 0
        skipped = 0

        try:
            with ZipFile(io.BytesIO(dataset.content)) as archive:
                entries = sorted(
                    (
                        entry
                        for entry in archive.infolist()
                        if UNLOCODE_FILE_PATTERN.search(entry.filename)
                    ),
                    key=lambda entry: entry.filename,
                )
                if not entries:
                    raise PortSchemaError("UN/LOCODE archive has no publication CSV parts")
                for entry in entries:
                    with archive.open(entry) as binary_stream:
                        text_stream = io.TextIOWrapper(
                            binary_stream, encoding="utf-8-sig", newline=""
                        )
                        for row_number, row in enumerate(csv.reader(text_stream), start=1):
                            if _is_empty_row(row) or _is_unlocode_country_header(row):
                                continue
                            received += 1
                            if len(row) != len(UNLOCODE_COLUMNS):
                                rejected += 1
                                issues["provider_revision"] += 1
                                continue
                            raw = dict(zip(UNLOCODE_COLUMNS, row, strict=True))
                            function_code = raw["function"].strip()
                            if len(function_code) != 8:
                                rejected += 1
                                issues["unknown_enum"] += 1
                                continue
                            if function_code[0] != "1":
                                skipped += 1
                                continue

                            record, record_issues = _normalize_unlocode_record(
                                raw, entry.filename, row_number
                            )
                            if record is None:
                                rejected += 1
                            else:
                                records.append(record)
                            issues.update(record_issues)
        except BadZipFile as error:
            raise PortSchemaError("UN/LOCODE artifact is not a readable ZIP archive") from error

        return PortParseResult(
            records=tuple(records),
            records_received=received,
            records_rejected=rejected,
            records_skipped=skipped,
            quality_counts=dict(issues),
        )


class WorldPortIndexParser:
    normalization_version = "wpi-port-normalizer-v1"

    def parse(self, dataset: FetchedPortDataset) -> PortParseResult:
        try:
            text_stream = io.StringIO(dataset.content.decode("utf-8-sig"), newline="")
        except UnicodeDecodeError as error:
            raise PortSchemaError("WPI CSV is not valid UTF-8") from error

        reader = csv.DictReader(text_stream)
        if reader.fieldnames is None:
            raise PortSchemaError("WPI CSV header is missing")
        missing = WPI_REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise PortSchemaError(f"WPI CSV is missing required columns: {sorted(missing)}")

        records: list[NormalizedPortSourceRecord] = []
        issues: Counter[str] = Counter()
        received = 0
        rejected = 0
        for row in reader:
            if row is None or not any((value or "").strip() for value in row.values()):
                continue
            received += 1
            record, record_issues = _normalize_wpi_record(row)
            if record is None:
                rejected += 1
            else:
                records.append(record)
            issues.update(record_issues)

        return PortParseResult(
            records=tuple(records),
            records_received=received,
            records_rejected=rejected,
            records_skipped=0,
            quality_counts=dict(issues),
        )


def _normalize_unlocode_record(
    raw: dict[str, str], filename: str, row_number: int
) -> tuple[NormalizedPortSourceRecord | None, Counter[str]]:
    issues: Counter[str] = Counter()
    country_code = raw["country"].strip().upper()
    location_code = raw["location"].strip().upper()
    name = raw["name"].strip()
    un_locode = country_code + location_code
    if not name or not UNLOCODE_CODE_PATTERN.fullmatch(un_locode):
        issues["missing_required"] += 1
        return None, issues

    latitude: float | None = None
    longitude: float | None = None
    coordinate_accuracy: str | None = None
    coordinates = raw["coordinates"].strip()
    if coordinates:
        try:
            latitude, longitude = parse_unlocode_coordinates(coordinates)
            coordinate_accuracy = "one_arc_minute"
        except ValueError:
            issues["invalid_coordinate"] += 1

    row_fingerprint = hashlib.sha256(
        "\x1f".join(raw[column] for column in UNLOCODE_COLUMNS).encode("utf-8")
    ).hexdigest()
    flags = tuple(sorted(issues))
    return (
        NormalizedPortSourceRecord(
            source_record_key=f"{un_locode}:{row_fingerprint}",
            source_record_id=un_locode,
            record_type="unlocode",
            name=name,
            country_code=country_code,
            un_locode=un_locode,
            longitude=longitude,
            latitude=latitude,
            coordinate_accuracy=coordinate_accuracy,
            function_code=raw["function"].strip(),
            source_status=raw["status"].strip() or None,
            source_updated_value=raw["date"].strip() or None,
            quality_flags=flags,
            raw_record={
                **raw,
                "_source_file": filename,
                "_source_row": row_number,
            },
        ),
        issues,
    )


def _normalize_wpi_record(
    raw: dict[str, str | None],
) -> tuple[NormalizedPortSourceRecord | None, Counter[str]]:
    issues: Counter[str] = Counter()
    port_number = (raw.get("portNumber") or "").strip()
    name = (raw.get("portName") or "").strip()
    country_code = (raw.get("countryCode") or "").strip().upper()
    try:
        if int(port_number) <= 0:
            raise ValueError
    except ValueError:
        issues["missing_required"] += 1
        return None, issues
    if not name or not re.fullmatch(r"[A-Z]{2}", country_code):
        issues["missing_required"] += 1
        return None, issues

    try:
        latitude = parse_wpi_coordinate((raw.get("latitude") or "").strip(), latitude=True)
        longitude = parse_wpi_coordinate((raw.get("longitude") or "").strip(), latitude=False)
    except ValueError:
        issues["invalid_coordinate"] += 1
        return None, issues

    un_locode_value = (raw.get("unloCode") or "").replace(" ", "").strip().upper()
    un_locode: str | None = None
    if un_locode_value:
        if UNLOCODE_CODE_PATTERN.fullmatch(un_locode_value):
            un_locode = un_locode_value
            if un_locode[:2] != country_code:
                issues["identity_conflict"] += 1
        else:
            issues["identity_conflict"] += 1

    flags = tuple(sorted(issues))
    return (
        NormalizedPortSourceRecord(
            source_record_key=port_number,
            source_record_id=port_number,
            record_type="wpi",
            name=name,
            country_code=country_code,
            un_locode=un_locode,
            longitude=longitude,
            latitude=latitude,
            coordinate_accuracy="source_reported_dms",
            function_code=None,
            source_status=None,
            source_updated_value=None,
            quality_flags=flags,
            raw_record={key: value for key, value in raw.items() if key is not None},
        ),
        issues,
    )


def parse_unlocode_coordinates(value: str) -> tuple[float, float]:
    match = UNLOCODE_COORDINATE_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("invalid UN/LOCODE coordinate")
    lat_deg, lat_min, lat_hemisphere, lon_deg, lon_min, lon_hemisphere = match.groups()
    latitude = _degrees_minutes(int(lat_deg), int(lat_min), lat_hemisphere, latitude=True)
    longitude = _degrees_minutes(int(lon_deg), int(lon_min), lon_hemisphere, latitude=False)
    return latitude, longitude


def parse_wpi_coordinate(value: str, *, latitude: bool) -> float:
    match = WPI_COORDINATE_PATTERN.fullmatch(value)
    if match is None:
        raise ValueError("invalid WPI coordinate")
    degrees_text, minutes_text, seconds_text, hemisphere = match.groups()
    if latitude and hemisphere not in {"N", "S"}:
        raise ValueError("invalid latitude hemisphere")
    if not latitude and hemisphere not in {"E", "W"}:
        raise ValueError("invalid longitude hemisphere")
    degrees = int(degrees_text)
    minutes = int(minutes_text)
    seconds = float(seconds_text)
    maximum = 90 if latitude else 180
    if degrees > maximum or minutes >= 60 or seconds >= 60:
        raise ValueError("coordinate is out of range")
    if degrees == maximum and (minutes != 0 or seconds != 0):
        raise ValueError("coordinate exceeds axis limit")
    result = degrees + minutes / 60 + seconds / 3600
    if hemisphere in {"S", "W"}:
        result = -result
    return round(result, 8)


def _degrees_minutes(degrees: int, minutes: int, hemisphere: str, *, latitude: bool) -> float:
    maximum = 90 if latitude else 180
    if minutes >= 60 or degrees > maximum:
        raise ValueError("coordinate is out of range")
    if degrees == maximum and minutes != 0:
        raise ValueError("coordinate exceeds axis limit")
    result = degrees + minutes / 60
    if hemisphere in {"S", "W"}:
        result = -result
    return round(result, 6)


def _is_empty_row(row: Iterable[str]) -> bool:
    return not any(value.strip() for value in row)


def _is_unlocode_country_header(row: list[str]) -> bool:
    return len(row) >= 4 and not row[2].strip() and row[3].lstrip().startswith(".")
