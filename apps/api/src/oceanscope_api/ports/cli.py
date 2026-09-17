from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from oceanscope_api.core.settings import get_settings
from oceanscope_api.ports.artifacts import LocalArtifactStore
from oceanscope_api.ports.download import HttpDownloader
from oceanscope_api.ports.parsers import UnLocodeParser, WorldPortIndexParser
from oceanscope_api.ports.providers import UnLocodeProvider, WorldPortIndexProvider
from oceanscope_api.ports.service import PortImportReport, PortImportService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Import official UN/LOCODE and NGA WPI reference datasets."
    )
    parser.add_argument(
        "--source",
        choices=("unlocode", "wpi", "all"),
        default="all",
        help="Official reference source to import.",
    )
    parser.add_argument(
        "--code-revision",
        required=True,
        help="Git commit or immutable build revision recorded in the ingestion run.",
    )
    parser.add_argument(
        "--data-directory",
        type=Path,
        help="Ignored runtime directory for immutable source artifacts.",
    )
    return parser


def main() -> None:
    arguments = build_parser().parse_args()
    settings = get_settings()
    if settings.database_url is None:
        raise SystemExit("OCEANSCOPE_DATABASE_URL is required")

    engine = create_engine(settings.database_url.get_secret_value())
    data_directory = arguments.data_directory or settings.data_directory
    reports: list[PortImportReport] = []
    try:
        with HttpDownloader() as downloader, Session(engine) as session:
            service = PortImportService(
                session,
                LocalArtifactStore(data_directory),
                code_revision=arguments.code_revision,
            )
            if arguments.source in {"unlocode", "all"}:
                reports.append(
                    service.import_dataset(UnLocodeProvider(downloader), UnLocodeParser())
                )
            if arguments.source in {"wpi", "all"}:
                reports.append(
                    service.import_dataset(
                        WorldPortIndexProvider(downloader), WorldPortIndexParser()
                    )
                )
    finally:
        engine.dispose()

    print(json.dumps([asdict(report) for report in reports], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
