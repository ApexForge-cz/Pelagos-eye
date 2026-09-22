from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from oceanscope_api.api.contracts.live_ais import LiveAisPosition
from oceanscope_api.live_ais import (
    PelyrNormalizationError,
    PelyrPositionNormalizer,
    PelyrSourceDirectory,
)

INGESTED_AT = datetime(2026, 9, 22, 12, 0, 1, tzinfo=UTC)
NORMALIZED_AT = datetime(2026, 9, 22, 12, 0, 2, tzinfo=UTC)


def source_directory() -> PelyrSourceDirectory:
    # TEST DATA: fictional source metadata; never imported by production configuration.
    return PelyrSourceDirectory.from_provider_entries(
        [
            {
                "id": 1,
                "license": "LicenseRef-Pelyr-1.1",
                "attribution": "AIS data from Pelyr (pelyr.com), Pelyr Data Licence 1.1",
            },
            {
                "id": 100,
                "license": "CC-BY-4.0",
                "attribution": "Traffic data from Fintraffic / digitraffic.fi",
            },
            {
                "id": 102,
                "license": "NLOD-2.0",
                "attribution": "Data from Kystverket / kystverket.no",
            },
            {
                "id": 104,
                "license": "NLOD",
                "attribution": "BarentsWatch Live AIS",
            },
        ]
    )


def position_frame(**changes: object) -> dict[str, object]:
    # TEST DATA: fictional position frame; not captured from Pelyr or a credential-backed run.
    data: dict[str, object] = {
        "schema": 1,
        "mmsi": 230000001,
        "msg_type": 1,
        "lat": 60.17,
        "lon": 24.94,
        "sog": 12.5,
        "cog": 91.25,
        "heading": 90,
        "rx_ts": "2026-09-22T12:00:00+03:00",
        "unknown_provider_field": {"must_not": "leak"},
    }
    for field in tuple(changes):
        if field in data:
            data[field] = changes.pop(field)
    frame: dict[str, object] = {
        "type": "position",
        "id": "test-position-001",
        "license": "100",
        "data": data,
    }
    frame.update(changes)
    return frame


def normalize(frame: dict[str, object]) -> LiveAisPosition:
    return PelyrPositionNormalizer().normalize(
        frame,
        source_directory(),
        ingested_at=INGESTED_AT,
        normalized_at=NORMALIZED_AT,
    )


def test_normalizes_position_and_preserves_runtime_source_provenance() -> None:
    position = normalize(position_frame())

    assert position.observation_id == "pelyr:100:230000001:2026-09-22T09:00:00Z"
    assert position.mmsi == "230000001"
    assert position.observed_at == datetime(2026, 9, 22, 9, 0, tzinfo=UTC)
    assert position.latitude == 60.17
    assert position.longitude == 24.94
    assert position.speed_over_ground_knots == 12.5
    assert position.course_over_ground_deg == 91.25
    assert position.true_heading_deg == 90
    assert position.navigational_status_code is None
    assert position.provenance.source_slug == "pelyr-open-ais"
    assert position.provenance.attribution_text == "Traffic data from Fintraffic / digitraffic.fi"
    assert position.provenance.data_version == "pelyr-v1/source-100/CC-BY-4.0"
    assert position.provenance.provider_message_type == "1"
    assert position.provenance.source_event_id == "test-position-001"
    assert position.provenance.ingested_at == INGESTED_AT
    assert position.provenance.normalized_at == NORMALIZED_AT
    assert position.provenance.source_state == "LIVE"
    assert position.provenance.cache_age_seconds is None
    assert "unknown_provider_field" not in position.model_dump()


@pytest.mark.parametrize("source_id", [1, 100, 102, 104])
def test_selects_attribution_for_each_reviewed_source(source_id: int) -> None:
    position = normalize(position_frame(license=source_id))

    expected = {
        1: "AIS data from Pelyr (pelyr.com), Pelyr Data Licence 1.1",
        100: "Traffic data from Fintraffic / digitraffic.fi",
        102: "Data from Kystverket / kystverket.no",
        104: "BarentsWatch Live AIS",
    }
    assert position.provenance.attribution_text == expected[source_id]


def test_preserves_nullable_ais_values_as_none() -> None:
    position = normalize(position_frame(sog=None, cog=None, heading=None))

    assert position.speed_over_ground_knots is None
    assert position.course_over_ground_deg is None
    assert position.true_heading_deg is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mmsi", "23000001"),
        ("lat", 90.0001),
        ("lon", -180.0001),
        ("sog", 102.3),
        ("cog", 360),
        ("heading", 360),
        ("rx_ts", "not-a-timestamp"),
    ],
)
def test_rejects_invalid_position_values(field: str, value: object) -> None:
    with pytest.raises(PelyrNormalizationError):
        normalize(position_frame(**{field: value}))


def test_rejects_naive_processing_timestamp() -> None:
    with pytest.raises(PelyrNormalizationError, match="ingested_at"):
        PelyrPositionNormalizer().normalize(
            position_frame(),
            source_directory(),
            ingested_at=datetime(2026, 9, 22, 12, 0, 1),
            normalized_at=NORMALIZED_AT,
        )


@pytest.mark.parametrize("field", ["type", "id", "license", "data"])
def test_rejects_missing_required_fields(field: str) -> None:
    frame = position_frame()
    frame.pop(field)

    with pytest.raises((PelyrNormalizationError, ValidationError)):
        normalize(frame)


@pytest.mark.parametrize("field", ["mmsi", "msg_type", "lat", "lon", "rx_ts"])
def test_rejects_missing_required_position_data(field: str) -> None:
    frame = position_frame()
    data = frame["data"]
    assert isinstance(data, dict)
    data.pop(field)

    with pytest.raises((PelyrNormalizationError, ValidationError)):
        normalize(frame)


def test_rejects_non_position_frame() -> None:
    with pytest.raises(PelyrNormalizationError, match="frame type"):
        normalize(position_frame(type="heartbeat"))


def test_rejects_unknown_license_source() -> None:
    with pytest.raises(PelyrNormalizationError, match="unknown Pelyr license"):
        normalize(position_frame(license=999))


@pytest.mark.parametrize(
    "entry",
    [
        {"id": 0, "license": "NOASSERTION", "attribution": ""},
        {"id": 7, "license": "NOASSERTION", "attribution": "Unknown"},
        {"id": 8, "license": "CC-BY-4.0", "attribution": ""},
    ],
)
def test_rejects_unpublishable_source_metadata(entry: dict[str, object]) -> None:
    directory = PelyrSourceDirectory.from_provider_entries([entry])

    with pytest.raises(PelyrNormalizationError):
        PelyrPositionNormalizer().normalize(
            position_frame(license=entry["id"]),
            directory,
            ingested_at=INGESTED_AT,
            normalized_at=NORMALIZED_AT,
        )
