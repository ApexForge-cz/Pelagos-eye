from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from oceanscope_api.core.settings import get_settings
from oceanscope_api.provenance.manifest import (
    IngestionManifestService,
    ManifestNotFoundError,
    SqlAlchemyIngestionManifestRepository,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export one internal ingestion run as a reproducibility manifest."
    )
    parser.add_argument("--ingestion-run-id", type=UUID, required=True)
    arguments = parser.parse_args()
    settings = get_settings()
    if settings.database_url is None:
        raise SystemExit("OCEANSCOPE_DATABASE_URL is required")

    engine = create_engine(settings.database_url.get_secret_value())
    try:
        with Session(engine) as session:
            try:
                manifest = IngestionManifestService(
                    SqlAlchemyIngestionManifestRepository(session)
                ).export(arguments.ingestion_run_id)
            except ManifestNotFoundError as error:
                raise SystemExit(str(error)) from error
    finally:
        engine.dispose()

    print(json.dumps(asdict(manifest), default=_json_default, indent=2, sort_keys=True))


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime, UUID)):
        return value.isoformat() if not isinstance(value, UUID) else str(value)
    raise TypeError(f"unsupported manifest value: {type(value).__name__}")


if __name__ == "__main__":
    main()
