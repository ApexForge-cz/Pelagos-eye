from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import ValidationError

from oceanscope_api.api.contracts.live_ais import live_ais_server_event_adapter

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=UTC)


def position_payload() -> dict[str, object]:
    # TEST DATA: contract-only values; this fixture is not importable from production config.
    return {
        "observation_id": "aisstream:366123456:2026-09-19T12:00:00Z",
        "mmsi": "366123456",
        "observed_at": NOW.isoformat(),
        "longitude": -74.01,
        "latitude": 40.7,
        "speed_over_ground_knots": 12.4,
        "course_over_ground_deg": 91.2,
        "true_heading_deg": 90,
        "navigational_status_code": 0,
        "quality_flags": [],
        "provenance": {
            "source_slug": "aisstream",
            "source_url": "wss://stream.aisstream.io/v0/stream",
            "attribution_text": "AISStream",
            "data_version": "stream:2026-09-19",
            "schema_version": "provider-envelope-unverified",
            "provider_message_type": "PositionReport",
            "source_event_id": None,
            "ingested_at": (NOW + timedelta(seconds=1)).isoformat(),
            "normalized_at": (NOW + timedelta(seconds=1, milliseconds=20)).isoformat(),
            "source_state": "LIVE",
            "cache_age_seconds": None,
        },
    }


def envelope(event: str) -> dict[str, object]:
    return {
        "protocol_version": "1.0",
        "event": event,
        "stream_epoch": str(uuid4()),
        "sequence": 42,
        "emitted_at": (NOW + timedelta(seconds=2)).isoformat(),
    }


def test_position_event_accepts_normalized_nullable_dynamic_fields() -> None:
    payload = envelope("vessel.position")
    payload["position"] = position_payload()

    parsed = live_ais_server_event_adapter.validate_python(payload)

    assert parsed.event == "vessel.position"
    assert parsed.position.mmsi == "366123456"
    assert parsed.position.provenance.source_state == "LIVE"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("mmsi", "123"),
        ("longitude", 181),
        ("speed_over_ground_knots", 102.3),
        ("course_over_ground_deg", 360),
        ("true_heading_deg", 511),
    ],
)
def test_position_event_rejects_invalid_or_provider_sentinel_values(
    field: str, value: object
) -> None:
    payload = envelope("vessel.position")
    position = position_payload()
    position[field] = value
    payload["position"] = position

    with pytest.raises(ValidationError):
        live_ais_server_event_adapter.validate_python(payload)


def test_cached_position_requires_cache_age() -> None:
    payload = envelope("vessel.position")
    position = position_payload()
    provenance = position["provenance"]
    assert isinstance(provenance, dict)
    provenance["source_state"] = "CACHED"
    payload["position"] = position

    with pytest.raises(ValidationError, match="cache_age_seconds"):
        live_ais_server_event_adapter.validate_python(payload)


def test_unavailable_snapshot_cannot_carry_positions() -> None:
    payload = envelope("vessel.snapshot")
    payload.update(
        {
            "availability": "DATA UNAVAILABLE",
            "source_state": "OFFLINE",
            "cache_age_seconds": None,
            "coverage": {
                "state": "COVERED",
                "description": "Configured demo-region coverage.",
                "bounds": {"west": -75, "south": 40, "east": -73, "north": 42},
                "effective_at": NOW.isoformat(),
            },
            "positions": [position_payload()],
            "truncated": False,
        }
    )

    with pytest.raises(ValidationError, match="unavailable snapshots"):
        live_ais_server_event_adapter.validate_python(payload)


def test_no_coverage_snapshot_cannot_carry_positions() -> None:
    payload = envelope("vessel.snapshot")
    payload.update(
        {
            "availability": "AVAILABLE",
            "source_state": "LIVE",
            "cache_age_seconds": None,
            "coverage": {
                "state": "NO COVERAGE",
                "description": "The requested region is outside the configured subscription.",
                "bounds": None,
                "effective_at": NOW.isoformat(),
            },
            "positions": [position_payload()],
            "truncated": False,
        }
    )

    with pytest.raises(ValidationError, match="no-coverage snapshots"):
        live_ais_server_event_adapter.validate_python(payload)


def test_gap_event_explicitly_disallows_replay_claims() -> None:
    payload = envelope("stream.gap")
    payload.update(
        {
            "gap_started_at": NOW.isoformat(),
            "gap_ended_at": (NOW + timedelta(seconds=30)).isoformat(),
            "reason": "provider_disconnect",
            "dropped_updates": None,
            "replay_available": True,
            "detail": "Provider continuity was interrupted.",
        }
    )

    with pytest.raises(ValidationError):
        live_ais_server_event_adapter.validate_python(payload)


def test_contract_rejects_unknown_fields() -> None:
    payload = envelope("vessel.position")
    payload["position"] = position_payload()
    payload["raw_provider_message"] = {"secret": "must not leak"}

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        live_ais_server_event_adapter.validate_python(payload)
