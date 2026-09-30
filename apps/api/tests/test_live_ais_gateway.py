import asyncio
import json
import time
import tracemalloc
from datetime import UTC, datetime, timedelta
from uuid import UUID

from oceanscope_api.api.contracts.live_ais import (
    LiveAisGapEvent,
    LiveAisPosition,
    LiveAisPositionEvent,
    LiveAisProvenance,
    LiveAisServerEvent,
    LiveAisSnapshotEvent,
    LiveAisStatusEvent,
)
from oceanscope_api.live_ais.gateway import LiveAisClient, LiveAisGateway, LiveAisGatewayConfig
from oceanscope_api.live_ais.worker import (
    PelyrWorkerGapEvent,
    PelyrWorkerMetrics,
    PelyrWorkerStatusEvent,
)

NOW = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)
EPOCH_ONE = "11111111-1111-4111-8111-111111111111"
EPOCH_TWO = "22222222-2222-4222-8222-222222222222"


def position(mmsi: str, *, longitude: float = 24.5, second: int = 0) -> LiveAisPosition:
    # TEST DATA: fictional values isolated to backend tests.
    observed_at = NOW + timedelta(seconds=second)
    return LiveAisPosition(
        observation_id=f"test:{mmsi}:{second}",
        mmsi=mmsi,
        observed_at=observed_at,
        longitude=longitude,
        latitude=60.0,
        speed_over_ground_knots=10.0,
        course_over_ground_deg=90.0,
        true_heading_deg=90,
        navigational_status_code=None,
        quality_flags=("TEST DATA",),
        provenance=LiveAisProvenance(
            source_slug="test-source",
            source_url="https://example.invalid/test-data",
            attribution_text="TEST DATA",
            data_version="test-v1",
            schema_version="test-v1",
            provider_message_type="TEST DATA",
            source_event_id=f"test-{mmsi}-{second}",
            ingested_at=observed_at,
            normalized_at=observed_at,
            source_state="LIVE",
            cache_age_seconds=None,
        ),
    )


def status(
    *,
    state: str = "CONNECTED",
    epoch: str | None = EPOCH_ONE,
    reason: str = "welcome_accepted",
) -> PelyrWorkerStatusEvent:
    source_state = "LIVE" if state == "CONNECTED" else "OFFLINE"
    availability = "AVAILABLE" if state == "CONNECTED" else "DATA UNAVAILABLE"
    return PelyrWorkerStatusEvent(
        event="worker.status",
        occurred_at=NOW,
        connection_state=state,  # type: ignore[arg-type]
        freshness=source_state,  # type: ignore[arg-type]
        availability=availability,  # type: ignore[arg-type]
        reason=reason,  # type: ignore[arg-type]
        reconnect_attempt=0,
        stream_epoch=epoch,
        replay_available=False,
        metrics=PelyrWorkerMetrics(),
    )


def gap(*, reason: str = "socket_closed") -> PelyrWorkerGapEvent:
    return PelyrWorkerGapEvent(
        event="stream.gap",
        occurred_at=NOW,
        stream_epoch=EPOCH_ONE,
        reason=reason,  # type: ignore[arg-type]
        replay_available=False,
        metrics=PelyrWorkerMetrics(),
    )


async def receive_and_mark(client: LiveAisClient) -> LiveAisServerEvent:
    event = await client.next_event()
    assert event is not None
    client.mark_sent(event)
    return event


def test_new_client_gets_unavailable_snapshot_first_without_key() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(worker_configured=False, now=lambda: NOW)
        client = gateway.register_client()
        assert client is not None

        first = await receive_and_mark(client)
        second = await receive_and_mark(client)

        assert isinstance(first, LiveAisSnapshotEvent)
        assert first.sequence == 0
        assert first.availability == "DATA UNAVAILABLE"
        assert first.positions == ()
        assert isinstance(second, LiveAisStatusEvent)
        assert second.sequence == 1

    asyncio.run(scenario())


def test_same_mmsi_updates_are_coalesced_before_sequence_assignment() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(
            worker_configured=True,
            config=LiveAisGatewayConfig(coalesce_seconds=0.01, maintenance_seconds=0.01),
            now=lambda: NOW,
        )
        gateway.status_sink(status())
        client = gateway.register_client()
        assert client is not None
        await receive_and_mark(client)
        await receive_and_mark(client)
        await gateway.start()
        try:
            gateway.position_sink(position("230000001", longitude=24.1, second=1))
            gateway.position_sink(position("230000001", longitude=24.2, second=2))

            event = await asyncio.wait_for(client.next_event(), timeout=1)
            assert event is not None
            client.mark_sent(event)
            assert event.event == "vessel.position"
            assert event.position.longitude == 24.2
            assert event.sequence == 2
            assert gateway.metrics.positions_coalesced == 1
            assert gateway.metrics.positions_published == 1
        finally:
            await gateway.stop()

    asyncio.run(scenario())


def test_latest_state_expires_after_five_minutes() -> None:
    async def scenario() -> None:
        clock = [100.0]
        gateway = LiveAisGateway(
            worker_configured=True,
            now=lambda: NOW,
            monotonic=lambda: clock[0],
        )
        gateway.status_sink(status())
        gateway.position_sink(position("230000001"))
        await gateway.flush_pending()
        assert gateway.latest_count == 1

        clock[0] += 300.0

        assert gateway.latest_count == 0
        assert gateway.metrics.expired_positions == 1

    asyncio.run(scenario())


def test_provider_gap_requires_snapshot_and_reconnect_rotates_epoch() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(worker_configured=True, now=lambda: NOW)
        gateway.status_sink(status(epoch=EPOCH_ONE))
        client = gateway.register_client()
        assert client is not None
        initial = await receive_and_mark(client)
        initial_status = await receive_and_mark(client)
        assert isinstance(initial, LiveAisSnapshotEvent)
        assert isinstance(initial_status, LiveAisStatusEvent)
        assert initial.stream_epoch == UUID(EPOCH_ONE)
        assert initial_status.sequence == 1

        gateway.gap_sink(gap())
        public_gap = await receive_and_mark(client)
        replacement = await receive_and_mark(client)
        assert isinstance(public_gap, LiveAisGapEvent)
        assert public_gap.replay_available is False
        assert isinstance(replacement, LiveAisSnapshotEvent)
        assert replacement.sequence == public_gap.sequence + 1

        gateway.status_sink(status(epoch=EPOCH_TWO))
        new_snapshot = await receive_and_mark(client)
        connected = await receive_and_mark(client)
        assert isinstance(new_snapshot, LiveAisSnapshotEvent)
        assert new_snapshot.stream_epoch == UUID(EPOCH_TWO)
        assert new_snapshot.sequence == 0
        assert isinstance(connected, LiveAisStatusEvent)
        assert connected.sequence == 1

    asyncio.run(scenario())


def test_ingress_overflow_emits_gap_then_truncated_snapshot() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(
            worker_configured=True,
            config=LiveAisGatewayConfig(ingress_capacity=2),
            now=lambda: NOW,
        )
        gateway.status_sink(status())
        client = gateway.register_client()
        assert client is not None
        await receive_and_mark(client)
        await receive_and_mark(client)

        for index in range(3):
            gateway.position_sink(position(f"23000000{index + 1}", second=index))
        await gateway.flush_pending()

        events = []
        while client.queue_depth:
            events.append(await receive_and_mark(client))
        assert [event.event for event in events[-3:]] == [
            "stream.gap",
            "vessel.snapshot",
            "stream.status",
        ]
        assert isinstance(events[-3], LiveAisGapEvent)
        assert events[-3].reason == "server_backpressure"
        assert isinstance(events[-2], LiveAisSnapshotEvent)
        assert events[-2].truncated is True
        assert isinstance(events[-1], LiveAisStatusEvent)
        assert events[-1].source_state == "DELAYED"
        assert gateway.metrics.positions_dropped >= 1
        assert gateway.metrics.server_gaps == 1

    asyncio.run(scenario())


def test_slow_client_recovers_without_breaking_other_client_sequence() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(
            worker_configured=True,
            config=LiveAisGatewayConfig(client_queue_capacity=4),
            now=lambda: NOW,
        )
        gateway.status_sink(status())
        slow = gateway.register_client()
        healthy = gateway.register_client()
        assert slow is not None and healthy is not None
        for client in (slow, healthy):
            await receive_and_mark(client)
            await receive_and_mark(client)

        for index in range(5):
            gateway.position_sink(position(f"2300000{index + 10}", second=index))
            await gateway.flush_pending()
            healthy_event = await receive_and_mark(healthy)
            assert isinstance(healthy_event, LiveAisPositionEvent)

        slow_gap = await receive_and_mark(slow)
        slow_snapshot = await receive_and_mark(slow)
        assert isinstance(slow_gap, LiveAisGapEvent)
        assert slow_gap.reason == "client_backpressure"
        assert slow_gap.sequence == 2
        assert isinstance(slow_snapshot, LiveAisSnapshotEvent)
        assert slow_snapshot.sequence == 3
        assert healthy.last_sent_sequence == 6
        assert gateway.metrics.client_gaps == 1

    asyncio.run(scenario())


def test_client_limit_and_second_overflow_disconnect_are_explicit() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(
            worker_configured=True,
            config=LiveAisGatewayConfig(client_capacity=1, client_queue_capacity=2),
            now=lambda: NOW,
        )
        gateway.status_sink(status())
        client = gateway.register_client()
        assert client is not None
        assert gateway.register_client() is None
        await receive_and_mark(client)
        await receive_and_mark(client)

        for index in range(4):
            gateway.position_sink(position(f"2300000{index + 20}", second=index))
            await gateway.flush_pending()

        assert client.closed is True
        assert gateway.client_count == 0
        assert gateway.metrics.clients_rejected == 1
        assert gateway.metrics.slow_clients_disconnected == 1

    asyncio.run(scenario())


def test_no_coverage_and_shutdown_keep_no_positions_or_queues() -> None:
    async def scenario() -> None:
        gateway = LiveAisGateway(
            worker_configured=True,
            coverage_state="NO COVERAGE",
            now=lambda: NOW,
        )
        gateway.status_sink(status())
        gateway.position_sink(position("230000001"))
        await gateway.flush_pending()
        snapshot = gateway.current_snapshot()
        assert snapshot.coverage.state == "NO COVERAGE"
        assert snapshot.positions == ()

        client = gateway.register_client()
        assert client is not None
        await gateway.start()
        await gateway.stop()
        assert gateway.latest_count == 0
        assert gateway.client_count == 0
        assert client.closed is True

    asyncio.run(scenario())


def test_synthetic_benchmark_stays_within_first_slice_memory_target() -> None:
    async def scenario() -> dict[str, int | float]:
        # SYNTHETIC BENCHMARK: fictional records; never written to production storage.
        tracemalloc.start()
        wall_started = time.perf_counter()
        cpu_started = time.process_time()
        gateway = LiveAisGateway(worker_configured=True, now=lambda: NOW)
        gateway.status_sink(status())

        for batch_start in range(0, 10_000, 1_000):
            for index in range(batch_start, batch_start + 1_000):
                gateway.position_sink(position(f"{230_000_000 + index:09d}", second=index))
            await gateway.flush_pending()

        snapshot = gateway.current_snapshot()
        clients = [gateway.register_client() for _ in range(25)]
        assert all(client is not None for client in clients)
        assert gateway.register_client() is None
        client_payloads: list[str] = []
        for client in clients:
            assert client is not None
            client_snapshot = await client.next_event()
            assert isinstance(client_snapshot, LiveAisSnapshotEvent)
            client_payloads.append(client_snapshot.model_dump_json())
        _, peak_bytes = tracemalloc.get_traced_memory()
        result: dict[str, int | float] = {
            "positions": gateway.latest_count,
            "snapshot_positions": len(snapshot.positions),
            "snapshot_bytes": len(snapshot.model_dump_json().encode("utf-8")),
            "queued_client_payload_bytes": sum(len(payload) for payload in client_payloads),
            "ingress_high_water": gateway.metrics.ingress_high_water,
            "client_queue_high_water": gateway.metrics.client_queue_high_water,
            "peak_bytes": peak_bytes,
            "wall_seconds": time.perf_counter() - wall_started,
            "cpu_seconds": time.process_time() - cpu_started,
            "milliseconds_per_position": ((time.perf_counter() - wall_started) * 1_000 / 10_000),
        }
        await gateway.stop()
        tracemalloc.stop()
        return result

    measured = asyncio.run(scenario())
    print(f"SYNTHETIC BENCHMARK {json.dumps(measured, sort_keys=True)}")
    assert measured["positions"] == 10_000
    assert measured["snapshot_positions"] == 5_000
    assert measured["peak_bytes"] < 128 * 1024 * 1024
