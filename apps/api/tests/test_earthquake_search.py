from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from oceanscope_api.api.routes.earthquakes import TSUNAMI_WARNING, search_earthquakes
from oceanscope_api.core.errors import InvalidQueryError, SourceDataUnavailableError
from oceanscope_api.earthquakes.contracts import (
    EarthquakeSearchQuery,
    EarthquakeSearchRecord,
    EarthquakeSearchResult,
)
from oceanscope_api.earthquakes.service import EarthquakeSearchService
from oceanscope_api.main import app
from oceanscope_api.status.contracts import SourceAvailabilitySnapshot

NOW = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)


def query(**overrides: object) -> EarthquakeSearchQuery:
    values: dict[str, object] = {
        "start_at": NOW - timedelta(hours=1),
        "end_at": NOW,
        "min_longitude": 100.0,
        "min_latitude": 20.0,
        "max_longitude": 130.0,
        "max_latitude": 40.0,
        "min_magnitude": 2.0,
        "limit": 25,
        "offset": 0,
    }
    values.update(overrides)
    return EarthquakeSearchQuery(**values)  # type: ignore[arg-type]


class StubRepository:
    last_query: EarthquakeSearchQuery | None = None

    def search(self, search_query: EarthquakeSearchQuery) -> EarthquakeSearchResult:
        self.last_query = search_query
        return EarthquakeSearchResult(records=(), total=0)


class OfflineAvailability:
    def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
        assert slug == "usgs-earthquakes"
        return SourceAvailabilitySnapshot(
            state="OFFLINE", has_usable_data=False, cache_age_seconds=None
        )


class MissingAvailability:
    def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
        assert slug == "usgs-earthquakes"
        return None


def test_search_service_accepts_bounded_utc_query() -> None:
    repository = StubRepository()
    search_query = query()

    result = EarthquakeSearchService(repository).search(search_query)

    assert result.total == 0
    assert repository.last_query == search_query


def test_search_service_rejects_expired_source_data() -> None:
    with pytest.raises(SourceDataUnavailableError, match="USGS"):
        EarthquakeSearchService(StubRepository(), OfflineAvailability()).search(query())


def test_search_service_rejects_missing_source_data() -> None:
    with pytest.raises(SourceDataUnavailableError, match="USGS"):
        EarthquakeSearchService(StubRepository(), MissingAvailability()).search(query())


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"start_at": NOW.replace(tzinfo=None)}, "UTC offsets"),
        ({"start_at": NOW}, "earlier than"),
        ({"start_at": NOW - timedelta(days=32)}, "31 days"),
        ({"min_longitude": 130.0}, "min_longitude"),
        ({"min_latitude": 40.0}, "min_latitude"),
    ],
)
def test_search_service_rejects_inconsistent_bounds(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(InvalidQueryError, match=message):
        EarthquakeSearchService(StubRepository()).search(query(**overrides))


class StubEarthquakeSearchService(EarthquakeSearchService):
    def __init__(self) -> None:
        pass

    def search(self, search_query: EarthquakeSearchQuery) -> EarthquakeSearchResult:
        assert search_query == query(limit=10, offset=5)
        return EarthquakeSearchResult(
            total=1,
            records=(
                EarthquakeSearchRecord(
                    id=UUID("00000000-0000-0000-0000-000000000001"),
                    event_id="test-event",
                    event_time=NOW - timedelta(minutes=10),
                    provider_updated_at=NOW - timedelta(minutes=5),
                    longitude=120.5,
                    latitude=30.25,
                    depth_km=8.0,
                    magnitude=2.5,
                    place="TEST DATA event",
                    event_type="earthquake",
                    provider_status="reviewed",
                    tsunami=False,
                    significance=100,
                    detail_url="https://example.test/event",
                    quality_flags=(),
                    normalized_at=NOW,
                    source_slug="test-source",
                    source_display_name="TEST DATA Source",
                    source_url="https://example.test/feed.geojson",
                    attribution_text="TEST DATA attribution",
                    data_version="TEST-DATA-1",
                    schema_version="test-schema-v1",
                    published_at=NOW,
                    retrieved_at=NOW,
                    ingested_at=NOW,
                    source_state="LIVE",
                    cache_age_seconds=None,
                ),
            ),
        )


def test_earthquake_endpoint_exposes_event_semantics_and_provenance() -> None:
    response = search_earthquakes(
        StubEarthquakeSearchService(),
        start_at=NOW - timedelta(hours=1),
        end_at=NOW,
        min_longitude=100,
        min_latitude=20,
        max_longitude=130,
        max_latitude=40,
        min_magnitude=2,
        limit=10,
        offset=5,
    )

    payload = response.model_dump(mode="json")
    assert payload["warning"] == TSUNAMI_WARNING
    assert payload["total"] == 1
    record = payload["records"][0]
    assert record["event_id"] == "test-event"
    assert record["depth_km"] == 8.0
    assert record["tsunami"] is False
    assert record["provenance"]["source_slug"] == "test-source"
    assert "raw_record" not in record


def test_earthquake_openapi_requires_bounds_and_caps_pages() -> None:
    operation = app.openapi()["paths"]["/earthquakes"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    for name in (
        "start_at",
        "end_at",
        "min_longitude",
        "min_latitude",
        "max_longitude",
        "max_latitude",
    ):
        assert parameters[name]["required"] is True
    assert parameters["limit"]["schema"]["maximum"] == 100
