from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from oceanscope_api.core.settings import get_settings
from oceanscope_api.earthquakes.artifacts import EarthquakeArtifactStore
from oceanscope_api.earthquakes.parser import UsgsEarthquakeParser
from oceanscope_api.earthquakes.provider import UsgsEarthquakeProvider
from oceanscope_api.earthquakes.service import EarthquakeImportService
from oceanscope_api.ports.download import HttpDownloader


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the official USGS past-hour feed.")
    parser.add_argument("--code-revision", required=True)
    parser.add_argument("--data-directory", type=Path)
    arguments = parser.parse_args()
    settings = get_settings()
    if settings.database_url is None:
        raise SystemExit("OCEANSCOPE_DATABASE_URL is required")
    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with HttpDownloader() as downloader, Session(engine) as session:
            report = EarthquakeImportService(
                session,
                EarthquakeArtifactStore(arguments.data_directory or settings.data_directory),
                code_revision=arguments.code_revision,
            ).import_feed(UsgsEarthquakeProvider(downloader), UsgsEarthquakeParser())
    finally:
        engine.dispose()
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
