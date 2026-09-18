from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from oceanscope_api.api.routes.ocean import FORECAST_WARNING, query_marine_forecast
from oceanscope_api.core.errors import InvalidQueryError, SourceDataUnavailableError
from oceanscope_api.main import app
from oceanscope_api.ocean.contracts import (
    MarineForecastQuery,
    MarineForecastQueryResult,
    MarineForecastRecord,
)
from oceanscope_api.ocean.service import MarineForecastQueryService
from oceanscope_api.status.contracts import SourceAvailabilitySnapshot

NOW = datetime(2026, 9, 17, 12, 0, tzinfo=UTC)


def query(**overrides: object) -> MarineForecastQuery:
    values: dict[str, object] = {
        "latitude": 20.0,
        "longitude": -40.0,
        "start_at": NOW,
        "end_at": NOW + timedelta(days=1),
        "limit": 24,
        "offset": 0,
    }
    values.update(overrides)
    return MarineForecastQuery(**values)  # type: ignore[arg-type]


class StubRepository:
    last_query: MarineForecastQuery | None = None

    def query(self, forecast_query: MarineForecastQuery) -> MarineForecastQueryResult:
        self.last_query = forecast_query
        return MarineForecastQueryResult(records=(), total=0)


class OfflineAvailability:
    def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
        assert slug == "open-meteo-marine"
        return SourceAvailabilitySnapshot(
            state="OFFLINE", has_usable_data=False, cache_age_seconds=None
        )


class MissingAvailability:
    def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
        assert slug == "open-meteo-marine"
        return None


def test_query_service_accepts_bounded_utc_window() -> None:
    repository = StubRepository()
    forecast_query = query()

    result = MarineForecastQueryService(repository).query(forecast_query)

    assert result.total == 0
    assert repository.last_query == forecast_query


def test_query_service_rejects_expired_source_data() -> None:
    with pytest.raises(SourceDataUnavailableError, match="Open-Meteo"):
        MarineForecastQueryService(StubRepository(), OfflineAvailability()).query(query())


def test_query_service_rejects_missing_source_data() -> None:
    with pytest.raises(SourceDataUnavailableError, match="Open-Meteo"):
        MarineForecastQueryService(StubRepository(), MissingAvailability()).query(query())


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"start_at": NOW.replace(tzinfo=None)}, "UTC offsets"),
        ({"start_at": NOW + timedelta(days=1)}, "earlier than"),
        ({"end_at": NOW + timedelta(days=8)}, "7 days"),
    ],
)
def test_query_service_rejects_invalid_time_window(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(InvalidQueryError, match=message):
        MarineForecastQueryService(StubRepository()).query(query(**overrides))


class StubMarineForecastQueryService(MarineForecastQueryService):
    def __init__(self) -> None:
        pass

    def query(self, forecast_query: MarineForecastQuery) -> MarineForecastQueryResult:
        assert forecast_query == query(limit=10, offset=5)
        return MarineForecastQueryResult(
            total=1,
            records=(
                MarineForecastRecord(
                    id=UUID("00000000-0000-0000-0000-000000000001"),
                    requested_latitude=20.0,
                    requested_longitude=-40.0,
                    grid_latitude=20.041664,
                    grid_longitude=-40.041656,
                    valid_at=NOW,
                    model="best_match",
                    wave_height_m=1.4,
                    wave_direction_deg=71,
                    wave_period_s=7.55,
                    sea_surface_temperature_c=27.6,
                    ocean_current_velocity_kmh=0.5,
                    ocean_current_direction_deg=225,
                    sea_level_height_msl_m=0.19,
                    units={"wave_height": "m", "time": "iso8601"},
                    quality_flags=(),
                    normalized_at=NOW,
                    source_slug="test-source",
                    source_display_name="TEST DATA Source",
                    source_url="https://example.test/marine",
                    attribution_text="TEST DATA attribution",
                    data_version="TEST-DATA-1",
                    schema_version="test-schema-v1",
                    published_at=None,
                    retrieved_at=NOW,
                    ingested_at=NOW,
                    source_state="LIVE",
                    cache_age_seconds=None,
                ),
            ),
        )


def test_forecast_endpoint_exposes_grid_units_warning_and_provenance() -> None:
    response = query_marine_forecast(
        StubMarineForecastQueryService(),
        latitude=20,
        longitude=-40,
        start_at=NOW,
        end_at=NOW + timedelta(days=1),
        limit=10,
        offset=5,
    )

    payload = response.model_dump(mode="json")
    assert payload["warning"] == FORECAST_WARNING
    assert payload["total"] == 1
    record = payload["records"][0]
    assert record["requested_latitude"] == 20
    assert record["grid_latitude"] == 20.041664
    assert record["wave_height_m"] == 1.4
    assert record["units"]["wave_height"] == "m"
    assert record["provenance"]["source_slug"] == "test-source"
    assert "raw_record" not in record


def test_forecast_openapi_requires_point_and_time_bounds() -> None:
    operation = app.openapi()["paths"]["/ocean/forecast"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    for name in ("latitude", "longitude", "start_at", "end_at"):
        assert parameters[name]["required"] is True
    assert parameters["limit"]["schema"]["maximum"] == 168
