from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from oceanscope_api.earthquakes.contracts import (
    EarthquakeSchemaError,
    FetchedEarthquakeFeed,
)
from oceanscope_api.ports.contracts import SourceDescriptor
from oceanscope_api.ports.download import HttpDownloader
from oceanscope_api.provenance.models import RedistributionStatus

USGS_ALL_HOUR_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"

USGS_SOURCE = SourceDescriptor(
    slug="usgs-earthquakes",
    display_name="USGS Earthquake Hazards Program",
    official_url="https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
    terms_url="https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits",
    attribution_text="U.S. Geological Survey Earthquake Hazards Program",
    license_identifier="US-PUBLIC-DOMAIN",
    redistribution_status=RedistributionStatus.ALLOWED,
    terms_reviewed_at=datetime(2026, 9, 17, tzinfo=UTC),
)


class UsgsEarthquakeProvider:
    source = USGS_SOURCE

    def __init__(self, downloader: HttpDownloader) -> None:
        self._downloader = downloader

    def fetch(self) -> FetchedEarthquakeFeed:
        response = self._downloader.get(USGS_ALL_HOUR_URL, max_bytes=16_000_000)
        try:
            document = json.loads(response.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise EarthquakeSchemaError("USGS feed is not valid JSON") from error
        metadata = document.get("metadata") if isinstance(document, dict) else None
        if not isinstance(metadata, dict):
            raise EarthquakeSchemaError("USGS feed metadata is missing")
        generated_ms = _required_integer(metadata, "generated")
        api_version = metadata.get("api")
        if not isinstance(api_version, str) or not api_version.strip():
            raise EarthquakeSchemaError("USGS feed API version is missing")

        content_hash = hashlib.sha256(response.content).hexdigest()
        return FetchedEarthquakeFeed(
            source=self.source,
            data_version=f"generated:{generated_ms}:sha256:{content_hash[:16]}",
            schema_version=f"usgs-geojson-api:{api_version.strip()}",
            source_url=USGS_ALL_HOUR_URL,
            content=response.content,
            checksum_sha256=content_hash,
            generated_at=datetime.fromtimestamp(generated_ms / 1000, tz=UTC),
            retrieved_at=datetime.now(UTC),
        )


def _required_integer(document: dict[str, Any], key: str) -> int:
    value = document.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise EarthquakeSchemaError(f"USGS feed {key} is invalid")
    return value
