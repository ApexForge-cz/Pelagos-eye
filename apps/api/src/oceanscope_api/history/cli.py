from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import UTC, date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from oceanscope_api.core.settings import get_settings
from oceanscope_api.history.artifacts import HistoricalAisArtifactStore
from oceanscope_api.history.contracts import HistoricalAisRequest
from oceanscope_api.history.parser import MarineCadastreCsvParser
from oceanscope_api.history.provider import MarineCadastreProvider
from oceanscope_api.history.service import HistoricalAisImportService


def _utc_datetime(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise argparse.ArgumentTypeError("expected an ISO 8601 date-time") from error
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("date-time must include a UTC offset")
    return parsed.astimezone(UTC)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a bounded official NOAA MarineCadastre historical AIS slice."
    )
    parser.add_argument("--archive-date", type=date.fromisoformat, required=True)
    parser.add_argument("--min-longitude", type=float, required=True)
    parser.add_argument("--min-latitude", type=float, required=True)
    parser.add_argument("--max-longitude", type=float, required=True)
    parser.add_argument("--max-latitude", type=float, required=True)
    parser.add_argument("--start-at", type=_utc_datetime, required=True)
    parser.add_argument("--end-at", type=_utc_datetime, required=True)
    parser.add_argument("--record-limit", type=int, default=5_000)
    parser.add_argument(
        "--archive-path",
        type=Path,
        help="Previously downloaded official .zst archive; avoids downloading it again.",
    )
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--data-directory", type=Path)
    arguments = parser.parse_args()
    request = HistoricalAisRequest(
        archive_date=arguments.archive_date,
        min_longitude=arguments.min_longitude,
        min_latitude=arguments.min_latitude,
        max_longitude=arguments.max_longitude,
        max_latitude=arguments.max_latitude,
        start_at=arguments.start_at,
        end_at=arguments.end_at,
        record_limit=arguments.record_limit,
    )
    settings = get_settings()
    if settings.database_url is None:
        raise SystemExit("OCEANSCOPE_DATABASE_URL is required")
    data_directory = arguments.data_directory or settings.data_directory
    staging_directory = data_directory / "staging"
    staging_directory.mkdir(parents=True, exist_ok=True)
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with (
            TemporaryDirectory(prefix="marinecadastre-", dir=staging_directory) as temporary,
            MarineCadastreProvider(
                Path(temporary), local_archive=arguments.archive_path
            ) as provider,
            Session(engine) as session,
        ):
            report = HistoricalAisImportService(
                session,
                HistoricalAisArtifactStore(data_directory),
                code_revision=arguments.code_revision,
            ).import_archive(provider, MarineCadastreCsvParser(), request)
    finally:
        engine.dispose()
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
