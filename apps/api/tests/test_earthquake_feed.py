import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import httpx

from oceanscope_api.earthquakes.contracts import FetchedEarthquakeFeed
from oceanscope_api.earthquakes.parser import UsgsEarthquakeParser
from oceanscope_api.earthquakes.provider import (
    USGS_ALL_HOUR_URL,
    USGS_SOURCE,
    UsgsEarthquakeProvider,
)
from oceanscope_api.ports.download import HttpDownloader

GENERATED_MS = 1_789_632_000_000


def feed_document(*, longitude: object = 120.5, event_id: object = "test-event") -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "metadata": {"generated": GENERATED_MS, "count": 1, "api": "TEST-DATA"},
        "features": [
            {
                "type": "Feature",
                "id": event_id,
                "properties": {
                    "mag": 2.5,
                    "place": "TEST DATA event",
                    "time": GENERATED_MS - 100_000,
                    "updated": GENERATED_MS - 50_000,
                    "status": "reviewed",
                    "tsunami": 0,
                    "sig": 100,
                    "type": "earthquake",
                    "detail": "https://example.test/event",
                },
                "geometry": {"type": "Point", "coordinates": [longitude, 30.25, 8.0]},
            }
        ],
    }


def dataset(document: dict[str, Any]) -> FetchedEarthquakeFeed:
    content = json.dumps(document).encode()
    return FetchedEarthquakeFeed(
        source=USGS_SOURCE,
        data_version="TEST-DATA",
        schema_version="TEST-DATA-schema",
        source_url=USGS_ALL_HOUR_URL,
        content=content,
        checksum_sha256=hashlib.sha256(content).hexdigest(),
        generated_at=datetime.fromtimestamp(GENERATED_MS / 1000, tz=UTC),
        retrieved_at=datetime.fromtimestamp(GENERATED_MS / 1000, tz=UTC),
    )


def test_parser_preserves_event_and_separates_depth() -> None:
    parsed = UsgsEarthquakeParser().parse(dataset(feed_document()))

    assert parsed.records_received == 1
    assert parsed.records_rejected == 0
    event = parsed.records[0]
    assert event.event_id == "test-event"
    assert event.longitude == 120.5
    assert event.latitude == 30.25
    assert event.depth_km == 8.0
    assert event.tsunami is False


def test_parser_rejects_invalid_coordinate_without_zero_fill() -> None:
    parsed = UsgsEarthquakeParser().parse(dataset(feed_document(longitude=999)))

    assert parsed.records == []
    assert parsed.records_rejected == 1
    assert parsed.quality_counts == {"invalid_coordinate": 1}


def test_parser_rejects_duplicate_event_id_within_feed() -> None:
    document = feed_document()
    document["features"].append(document["features"][0])
    document["metadata"]["count"] = 2

    parsed = UsgsEarthquakeParser().parse(dataset(document))

    assert len(parsed.records) == 1
    assert parsed.records_rejected == 1
    assert parsed.quality_counts == {"duplicate": 1}


def test_provider_versions_feed_by_generated_time_and_checksum() -> None:
    content = json.dumps(feed_document()).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == USGS_ALL_HOUR_URL
        return httpx.Response(200, content=content, headers={"content-type": "application/json"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        fetched = UsgsEarthquakeProvider(HttpDownloader(client)).fetch()

    checksum = hashlib.sha256(content).hexdigest()
    assert fetched.data_version == f"generated:{GENERATED_MS}:sha256:{checksum[:16]}"
    assert fetched.checksum_sha256 == checksum
    assert fetched.schema_version == "usgs-geojson-api:TEST-DATA"
