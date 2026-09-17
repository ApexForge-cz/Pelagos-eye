import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx
import pytest

from oceanscope_api.ocean.contracts import FetchedMarineForecast, MarineForecastRequest
from oceanscope_api.ocean.parser import OpenMeteoMarineParser
from oceanscope_api.ocean.provider import OPEN_METEO_MARINE_SOURCE, OpenMeteoMarineProvider
from oceanscope_api.ports.download import HttpDownloader


def forecast_document(*, first_wave_height: object = 1.4) -> dict[str, Any]:
    return {
        "latitude": 20.041664,
        "longitude": -40.041656,
        "generationtime_ms": 0.2,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "hourly_units": {
            "time": "iso8601",
            "wave_height": "m",
            "wave_direction": "°",
            "wave_period": "s",
            "sea_surface_temperature": "°C",
            "ocean_current_velocity": "km/h",
            "ocean_current_direction": "°",
            "sea_level_height_msl": "m",
        },
        "hourly": {
            "time": ["2026-09-17T12:00", "2026-09-17T13:00"],
            "wave_height": [first_wave_height, 1.5],
            "wave_direction": [71, 72],
            "wave_period": [7.55, 7.5],
            "sea_surface_temperature": [27.6, 27.7],
            "ocean_current_velocity": [0.5, 0.6],
            "ocean_current_direction": [225, 236],
            "sea_level_height_msl": [0.19, 0.18],
        },
    }


def dataset(document: dict[str, Any]) -> FetchedMarineForecast:
    content = json.dumps(document).encode()
    return FetchedMarineForecast(
        source=OPEN_METEO_MARINE_SOURCE,
        request=MarineForecastRequest(latitude=20, longitude=-40, forecast_hours=2),
        data_version="TEST-DATA",
        schema_version="TEST-DATA-schema",
        source_url="https://example.test/marine",
        content=content,
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        retrieved_at=datetime(2026, 9, 17, 12, tzinfo=UTC),
    )


def test_request_enforces_bounded_forecast() -> None:
    with pytest.raises(ValueError, match="forecast_hours"):
        MarineForecastRequest(latitude=20, longitude=-40, forecast_hours=169)


def test_parser_preserves_units_grid_and_utc_valid_time() -> None:
    parsed = OpenMeteoMarineParser().parse(dataset(forecast_document()))

    assert parsed.records_received == 2
    assert parsed.records_rejected == 0
    point = parsed.records[0]
    assert point.valid_at == datetime(2026, 9, 17, 12, tzinfo=UTC)
    assert point.requested_latitude == 20
    assert point.grid_latitude == 20.041664
    assert point.wave_height_m == 1.4
    assert point.units["ocean_current_velocity"] == "km/h"


def test_parser_rejects_out_of_range_value_without_clamping() -> None:
    parsed = OpenMeteoMarineParser().parse(dataset(forecast_document(first_wave_height=-1)))

    assert len(parsed.records) == 1
    assert parsed.records_rejected == 1
    assert parsed.quality_counts == {"out_of_range": 1}


def test_parser_rejects_row_when_all_values_are_null() -> None:
    document = forecast_document()
    for variable, values in document["hourly"].items():
        if variable != "time":
            values[0] = None

    parsed = OpenMeteoMarineParser().parse(dataset(document))

    assert len(parsed.records) == 1
    assert parsed.records_rejected == 1
    assert parsed.quality_counts == {"coverage_unknown": 1}


def test_provider_uses_bounded_utc_sea_cell_request() -> None:
    content = json.dumps(forecast_document()).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        query = parse_qs(urlparse(str(request.url)).query)
        assert query["forecast_hours"] == ["2"]
        assert query["timezone"] == ["GMT"]
        assert query["cell_selection"] == ["sea"]
        assert query["models"] == ["best_match"]
        assert set(query["hourly"][0].split(",")) == set(MarineForecastRequest(20, -40).variables)
        return httpx.Response(200, content=content, headers={"content-type": "application/json"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = OpenMeteoMarineProvider(HttpDownloader(client)).fetch(
            MarineForecastRequest(latitude=20, longitude=-40, forecast_hours=2)
        )

    checksum = hashlib.sha256(content).hexdigest()
    assert fetched.data_version.endswith(f"sha256:{checksum[:16]}")
    assert fetched.checksum_sha256 == checksum
