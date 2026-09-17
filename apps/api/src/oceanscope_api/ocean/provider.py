from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlencode

from oceanscope_api.ocean.contracts import (
    FetchedMarineForecast,
    MarineDownloadError,
    MarineForecastRequest,
    MarineSchemaError,
)
from oceanscope_api.ports.contracts import PortDataError, SourceDescriptor
from oceanscope_api.ports.download import HttpDownloader
from oceanscope_api.provenance.models import RedistributionStatus

OPEN_METEO_MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"

OPEN_METEO_MARINE_SOURCE = SourceDescriptor(
    slug="open-meteo-marine",
    display_name="Open-Meteo Marine Weather API",
    official_url="https://open-meteo.com/en/docs/marine-weather-api",
    terms_url="https://open-meteo.com/en/terms",
    attribution_text=(
        "Weather data by Open-Meteo.com (CC BY 4.0); underlying marine model providers "
        "are documented by Open-Meteo"
    ),
    license_identifier="CC-BY-4.0",
    redistribution_status=RedistributionStatus.ALLOWED,
    terms_reviewed_at=datetime(2026, 9, 17, tzinfo=UTC),
)


class OpenMeteoMarineProvider:
    source = OPEN_METEO_MARINE_SOURCE

    def __init__(self, downloader: HttpDownloader) -> None:
        self._downloader = downloader

    def fetch(self, request: MarineForecastRequest) -> FetchedMarineForecast:
        query = urlencode(
            {
                "latitude": f"{request.latitude:.6f}",
                "longitude": f"{request.longitude:.6f}",
                "hourly": ",".join(request.variables),
                "forecast_hours": request.forecast_hours,
                "timezone": "GMT",
                "cell_selection": "sea",
                "models": request.model,
            }
        )
        requested_url = f"{OPEN_METEO_MARINE_URL}?{query}"
        try:
            response = self._downloader.get(requested_url, max_bytes=4_000_000)
        except PortDataError as error:
            raise MarineDownloadError(str(error)) from error
        try:
            document = json.loads(response.content)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise MarineSchemaError("Open-Meteo response is not valid JSON") from error
        if not isinstance(document, dict) or not isinstance(document.get("hourly"), dict):
            raise MarineSchemaError("Open-Meteo hourly forecast is missing")
        checksum = hashlib.sha256(response.content).hexdigest()
        hourly = document["hourly"]
        times = hourly.get("time")
        if (
            not isinstance(times, list)
            or not times
            or not all(isinstance(value, str) for value in times)
        ):
            raise MarineSchemaError("Open-Meteo forecast times are missing")
        return FetchedMarineForecast(
            source=self.source,
            request=request,
            data_version=f"forecast:{times[0]}:{times[-1]}:sha256:{checksum[:16]}",
            schema_version="open-meteo-marine-v1",
            source_url=response.url,
            content=response.content,
            checksum_sha256=checksum,
            retrieved_at=datetime.now(UTC),
        )
