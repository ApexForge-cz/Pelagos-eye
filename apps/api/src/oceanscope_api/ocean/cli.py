from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from oceanscope_api.core.settings import get_settings
from oceanscope_api.ocean.artifacts import MarineForecastArtifactStore
from oceanscope_api.ocean.contracts import MarineForecastRequest
from oceanscope_api.ocean.parser import OpenMeteoMarineParser
from oceanscope_api.ocean.provider import OpenMeteoMarineProvider
from oceanscope_api.ocean.service import MarineForecastImportService
from oceanscope_api.ports.download import HttpDownloader


def main() -> None:
    argument_parser = argparse.ArgumentParser(
        description="Import a bounded official Open-Meteo marine forecast."
    )
    argument_parser.add_argument("--latitude", type=float, required=True)
    argument_parser.add_argument("--longitude", type=float, required=True)
    argument_parser.add_argument("--forecast-hours", type=int, default=24)
    argument_parser.add_argument("--code-revision", required=True)
    argument_parser.add_argument("--data-directory", type=Path)
    arguments = argument_parser.parse_args()
    request = MarineForecastRequest(
        latitude=arguments.latitude,
        longitude=arguments.longitude,
        forecast_hours=arguments.forecast_hours,
    )
    settings = get_settings()
    if settings.database_url is None:
        raise SystemExit("OCEANSCOPE_DATABASE_URL is required")
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with HttpDownloader() as downloader, Session(engine) as session:
            report = MarineForecastImportService(
                session,
                MarineForecastArtifactStore(arguments.data_directory or settings.data_directory),
                code_revision=arguments.code_revision,
            ).import_forecast(OpenMeteoMarineProvider(downloader), OpenMeteoMarineParser(), request)
    finally:
        engine.dispose()
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
