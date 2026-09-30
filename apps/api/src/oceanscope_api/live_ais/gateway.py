"""Bounded in-memory product delivery for the first Live AIS slice.

The gateway consumes only provider-neutral positions and bounded worker telemetry. It
owns no provider connection, persistence, replay, dynamic subscription, or export path.
"""

from __future__ import annotations

import asyncio
import math
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Final
from uuid import UUID, uuid4

from oceanscope_api.api.contracts.live_ais import (
    Availability,
    ConnectionState,
    LiveAisBounds,
    LiveAisCoverage,
    LiveAisGapEvent,
    LiveAisPosition,
    LiveAisPositionEvent,
    LiveAisServerEvent,
    LiveAisSnapshotEvent,
    LiveAisStatusEvent,
    SourceState,
)
from oceanscope_api.live_ais.worker import (
    PELYR_BOUNDS,
    PelyrWorkerGapEvent,
    PelyrWorkerStatusEvent,
)

GULF_COVERAGE_DESCRIPTION: Final = (
    "Fixed Gulf of Finland pilot coverage; reporting is incomplete and not navigational."
)
NO_COVERAGE_DESCRIPTION: Final = "The requested scope is outside the fixed pilot coverage."


@dataclass(frozen=True, slots=True)
class LiveAisGatewayConfig:
    ingress_capacity: int = 2_048
    latest_capacity: int = 10_000
    snapshot_capacity: int = 5_000
    client_queue_capacity: int = 256
    client_capacity: int = 25
    coalesce_seconds: float = 0.250
    latest_ttl_seconds: float = 300.0
    maintenance_seconds: float = 1.0

    def __post_init__(self) -> None:
        integer_limits = (
            self.ingress_capacity,
            self.latest_capacity,
            self.snapshot_capacity,
            self.client_queue_capacity,
            self.client_capacity,
        )
        if any(isinstance(value, bool) or value <= 0 for value in integer_limits):
            raise ValueError("gateway capacities must be positive integers")
        if self.client_queue_capacity < 2:
            raise ValueError("client queue capacity must hold a gap and replacement snapshot")
        durations = (
            self.coalesce_seconds,
            self.latest_ttl_seconds,
            self.maintenance_seconds,
        )
        if any(not math.isfinite(value) or value <= 0 for value in durations):
            raise ValueError("gateway durations must be positive finite values")
        if self.coalesce_seconds > 0.250:
            raise ValueError("same-MMSI coalescing must not exceed 250 milliseconds")


@dataclass(frozen=True, slots=True)
class LiveAisGatewayMetrics:
    ingress_high_water: int = 0
    client_queue_high_water: int = 0
    positions_received: int = 0
    positions_published: int = 0
    positions_coalesced: int = 0
    positions_dropped: int = 0
    expired_positions: int = 0
    provider_gaps: int = 0
    server_gaps: int = 0
    client_gaps: int = 0
    snapshots_emitted: int = 0
    snapshot_high_water: int = 0
    clients_connected: int = 0
    clients_rejected: int = 0
    slow_clients_disconnected: int = 0
    max_coalesce_latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class _StoredPosition:
    position: LiveAisPosition
    received_at: float


@dataclass(frozen=True, slots=True)
class _CloseSignal:
    reason: str


ClientQueueItem = LiveAisServerEvent | _CloseSignal
EventFactory = Callable[[UUID, int, datetime], LiveAisServerEvent]


class LiveAisClient:
    """One bounded client queue with an independent contiguous public sequence."""

    def __init__(self, *, capacity: int, stream_epoch: UUID) -> None:
        self._queue: asyncio.Queue[ClientQueueItem] = asyncio.Queue(maxsize=capacity)
        self._stream_epoch = stream_epoch
        self._next_sequence = 0
        self._last_sent_sequence = -1
        self._recovering = False
        self._closed = False

    @property
    def stream_epoch(self) -> UUID:
        return self._stream_epoch

    @property
    def queue_depth(self) -> int:
        return self._queue.qsize()

    @property
    def available_slots(self) -> int:
        return self._queue.maxsize - self._queue.qsize()

    @property
    def last_sent_sequence(self) -> int:
        return self._last_sent_sequence

    @property
    def recovering(self) -> bool:
        return self._recovering

    @property
    def closed(self) -> bool:
        return self._closed

    async def next_event(self) -> LiveAisServerEvent | None:
        item = await self._queue.get()
        if isinstance(item, _CloseSignal):
            return None
        return item

    def mark_sent(self, event: LiveAisServerEvent) -> None:
        if event.stream_epoch != self._stream_epoch:
            return
        self._last_sent_sequence = max(self._last_sent_sequence, event.sequence)
        if self._recovering and event.event == "vessel.snapshot":
            self._recovering = False

    def build(self, factory: EventFactory, now: datetime) -> LiveAisServerEvent:
        event = factory(self._stream_epoch, self._next_sequence, now)
        self._next_sequence += 1
        return event

    def put(self, event: LiveAisServerEvent) -> bool:
        if self._closed:
            return False
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            return False
        return True

    def reset_epoch(self, stream_epoch: UUID) -> None:
        self._clear_queue()
        self._stream_epoch = stream_epoch
        self._next_sequence = 0
        self._last_sent_sequence = -1
        self._recovering = False

    def begin_recovery(self) -> int | None:
        if self._closed or self._recovering or self._last_sent_sequence < 0:
            return None
        dropped = self._clear_queue()
        self._next_sequence = self._last_sent_sequence + 1
        self._recovering = True
        return dropped

    def close(self, reason: str) -> None:
        if self._closed:
            return
        self._closed = True
        self._clear_queue()
        self._queue.put_nowait(_CloseSignal(reason))

    def _clear_queue(self) -> int:
        removed = 0
        while True:
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                return removed
            removed += 1


class LiveAisGateway:
    """Bounded latest-state, coalescing, continuity, and client fan-out service."""

    def __init__(
        self,
        *,
        worker_configured: bool,
        config: LiveAisGatewayConfig | None = None,
        now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        epoch_factory: Callable[[], UUID] | None = None,
        coverage_state: str = "COVERED",
    ) -> None:
        if coverage_state not in {"COVERED", "NO COVERAGE"}:
            raise ValueError("coverage_state must be COVERED or NO COVERAGE")
        self._config = config or LiveAisGatewayConfig()
        self._now = now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic
        self._epoch_factory = epoch_factory or uuid4
        self._stream_epoch = self._epoch_factory()
        self._provider_epoch: str | None = None
        self._coverage_state = coverage_state
        self._coverage_effective_at = self._utc_now()
        self._ingress: asyncio.Queue[LiveAisPosition] = asyncio.Queue(
            maxsize=self._config.ingress_capacity
        )
        self._pending: dict[str, LiveAisPosition] = {}
        self._pending_since: float | None = None
        self._latest: dict[str, _StoredPosition] = {}
        self._clients: set[LiveAisClient] = set()
        self._consumer_task: asyncio.Task[None] | None = None
        self._server_overflow_pending = 0
        self._state_incomplete = False
        self._connection_state: ConnectionState = "DISCONNECTED"
        self._source_state: SourceState = "OFFLINE"
        self._availability: Availability = "DATA UNAVAILABLE"
        self._last_observation_at: datetime | None = None
        self._detail = (
            "Live AIS worker is starting."
            if worker_configured
            else "Server-side Pelyr key is not configured."
        )
        self._metrics = LiveAisGatewayMetrics()

    @property
    def metrics(self) -> LiveAisGatewayMetrics:
        return self._metrics

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def latest_count(self) -> int:
        self._expire_positions()
        return len(self._latest)

    async def start(self) -> None:
        if self._consumer_task is not None:
            raise RuntimeError("Live AIS gateway is already running")
        self._consumer_task = asyncio.create_task(
            self._consume_positions(), name="live-ais-gateway-consumer"
        )

    async def stop(self) -> None:
        task = self._consumer_task
        self._consumer_task = None
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        for client in tuple(self._clients):
            client.close("shutdown")
        self._clients.clear()
        self._pending.clear()
        self._latest.clear()
        self._pending_since = None
        self._server_overflow_pending = 0
        while True:
            try:
                self._ingress.get_nowait()
            except asyncio.QueueEmpty:
                break
        self._metrics = replace(self._metrics, clients_connected=0)

    def position_sink(self, position: LiveAisPosition) -> None:
        self._metrics = replace(
            self._metrics,
            positions_received=self._metrics.positions_received + 1,
        )
        try:
            self._ingress.put_nowait(position)
        except asyncio.QueueFull:
            self._server_overflow_pending += 1
            self._metrics = replace(
                self._metrics,
                positions_dropped=self._metrics.positions_dropped + 1,
            )
            return
        self._metrics = replace(
            self._metrics,
            ingress_high_water=max(self._metrics.ingress_high_water, self._ingress.qsize()),
        )

    def status_sink(self, status: PelyrWorkerStatusEvent) -> None:
        self._connection_state = status.connection_state
        self._source_state = status.freshness
        self._availability = status.availability
        self._detail = _status_detail(status.reason)

        if (
            status.connection_state == "CONNECTED"
            and status.stream_epoch is not None
            and status.stream_epoch != self._provider_epoch
        ):
            self._provider_epoch = status.stream_epoch
            try:
                new_epoch = UUID(status.stream_epoch)
            except ValueError:
                new_epoch = self._epoch_factory()
            self._latest.clear()
            self._pending.clear()
            self._pending_since = None
            self._state_incomplete = False
            self._rotate_epoch(new_epoch)
        self._broadcast(self._status_factory())

    def gap_sink(self, gap: PelyrWorkerGapEvent) -> None:
        self._pending.clear()
        self._pending_since = None
        self._latest.clear()
        self._connection_state = "RECONNECTING" if gap.reason != "shutdown" else "DISCONNECTED"
        self._source_state = "OFFLINE"
        self._availability = "DATA UNAVAILABLE"
        self._detail = "Upstream continuity ended; replay is unavailable."
        self._metrics = replace(
            self._metrics,
            provider_gaps=self._metrics.provider_gaps + 1,
        )
        self._broadcast_gap_and_snapshot(
            reason="provider_disconnect",
            dropped_updates=None,
            detail=self._detail,
            truncated=False,
        )

    def register_client(self) -> LiveAisClient | None:
        if len(self._clients) >= self._config.client_capacity:
            self._metrics = replace(
                self._metrics,
                clients_rejected=self._metrics.clients_rejected + 1,
            )
            return None
        client = LiveAisClient(
            capacity=self._config.client_queue_capacity,
            stream_epoch=self._stream_epoch,
        )
        self._clients.add(client)
        self._metrics = replace(
            self._metrics,
            clients_connected=len(self._clients),
        )
        self._enqueue(client, self._snapshot_factory(truncated=False), allow_recovery=False)
        self._enqueue(client, self._status_factory(), allow_recovery=False)
        return client

    def unregister_client(self, client: LiveAisClient) -> None:
        if client in self._clients:
            self._clients.remove(client)
        client.close("client_disconnected")
        self._metrics = replace(
            self._metrics,
            clients_connected=len(self._clients),
        )

    def current_snapshot(self, *, truncated: bool = False) -> LiveAisSnapshotEvent:
        """Build a bounded in-memory view without creating a public snapshot endpoint."""

        factory = self._snapshot_factory(truncated=truncated)
        event = factory(self._stream_epoch, 0, self._utc_now())
        if not isinstance(event, LiveAisSnapshotEvent):
            raise AssertionError("snapshot factory returned the wrong event")
        return event

    async def flush_pending(self) -> None:
        """Drain accepted ingress and publish one coalesced batch immediately."""

        while not self._ingress.empty():
            self._coalesce(self._ingress.get_nowait())
        self._flush_pending()
        if self._server_overflow_pending:
            self._handle_server_overflow()

    async def _consume_positions(self) -> None:
        while True:
            if self._server_overflow_pending:
                self._handle_server_overflow()
            timeout = self._next_timeout()
            try:
                position = await asyncio.wait_for(self._ingress.get(), timeout=timeout)
            except TimeoutError:
                if self._pending and self._coalesce_due():
                    self._flush_pending()
                self._expire_positions()
                continue
            self._coalesce(position)
            if self._coalesce_due():
                self._flush_pending()

    def _coalesce(self, position: LiveAisPosition) -> None:
        if position.mmsi in self._pending:
            self._metrics = replace(
                self._metrics,
                positions_coalesced=self._metrics.positions_coalesced + 1,
            )
        elif self._pending_since is None:
            self._pending_since = self._monotonic()
        self._pending[position.mmsi] = position

    def _flush_pending(self) -> None:
        pending = tuple(self._pending.values())
        pending_since = self._pending_since
        self._pending.clear()
        self._pending_since = None
        received_at = self._monotonic()
        if pending_since is not None:
            self._metrics = replace(
                self._metrics,
                max_coalesce_latency_ms=max(
                    self._metrics.max_coalesce_latency_ms,
                    max(0.0, (received_at - pending_since) * 1_000),
                ),
            )
        self._expire_positions(received_at)
        for index, position in enumerate(pending):
            if (
                position.mmsi not in self._latest
                and len(self._latest) >= self._config.latest_capacity
            ):
                self._handle_server_overflow(dropped_updates=len(pending) - index)
                break
            self._latest[position.mmsi] = _StoredPosition(position, received_at)
            if (
                self._last_observation_at is None
                or position.observed_at > self._last_observation_at
            ):
                self._last_observation_at = position.observed_at
            self._broadcast(self._position_factory(position))
            self._metrics = replace(
                self._metrics,
                positions_published=self._metrics.positions_published + 1,
            )

    def _handle_server_overflow(self, dropped_updates: int | None = None) -> None:
        pending_overflow = self._server_overflow_pending
        self._server_overflow_pending = 0
        self._pending.clear()
        self._pending_since = None
        drained = 0
        while True:
            try:
                self._ingress.get_nowait()
                drained += 1
            except asyncio.QueueEmpty:
                break
        if dropped_updates is None:
            dropped = pending_overflow + drained
            newly_counted = drained
        else:
            dropped = dropped_updates + pending_overflow + drained
            newly_counted = dropped_updates + drained
        self._state_incomplete = True
        if self._availability == "AVAILABLE":
            self._source_state = "DELAYED"
        self._detail = "Server backpressure interrupted continuity; snapshot is incomplete."
        self._metrics = replace(
            self._metrics,
            positions_dropped=self._metrics.positions_dropped + newly_counted,
            server_gaps=self._metrics.server_gaps + 1,
        )
        self._broadcast_gap_and_snapshot(
            reason="server_backpressure",
            dropped_updates=dropped,
            detail=self._detail,
            truncated=True,
        )
        self._broadcast(self._status_factory())

    def _broadcast_gap_and_snapshot(
        self,
        *,
        reason: str,
        dropped_updates: int | None,
        detail: str,
        truncated: bool,
    ) -> None:
        self._broadcast(self._gap_factory(reason, dropped_updates, detail))
        self._broadcast(self._snapshot_factory(truncated=truncated))

    def _rotate_epoch(self, stream_epoch: UUID) -> None:
        self._stream_epoch = stream_epoch
        for client in tuple(self._clients):
            client.reset_epoch(stream_epoch)
            self._enqueue(client, self._snapshot_factory(truncated=False), allow_recovery=False)

    def _broadcast(self, factory: EventFactory) -> None:
        for client in tuple(self._clients):
            self._enqueue(client, factory, allow_recovery=True)

    def _enqueue(
        self,
        client: LiveAisClient,
        factory: EventFactory,
        *,
        allow_recovery: bool,
    ) -> None:
        event = client.build(factory, self._utc_now())
        if client.put(event):
            self._record_client_queue_depth(client)
            if event.event == "vessel.snapshot":
                self._metrics = replace(
                    self._metrics,
                    snapshots_emitted=self._metrics.snapshots_emitted + 1,
                    snapshot_high_water=max(
                        self._metrics.snapshot_high_water, len(event.positions)
                    ),
                )
            return
        if not allow_recovery:
            self._disconnect_slow_client(client)
            return
        dropped = client.begin_recovery()
        if dropped is None:
            self._disconnect_slow_client(client)
            return
        self._metrics = replace(
            self._metrics,
            client_gaps=self._metrics.client_gaps + 1,
        )
        gap = client.build(
            self._gap_factory(
                "client_backpressure",
                dropped,
                "Slow-client backpressure interrupted continuity.",
            ),
            self._utc_now(),
        )
        snapshot = client.build(self._snapshot_factory(truncated=True), self._utc_now())
        if not client.put(gap) or not client.put(snapshot):
            self._disconnect_slow_client(client)
            return
        self._record_client_queue_depth(client)
        if client.available_slots:
            status = client.build(self._status_factory(), self._utc_now())
            if client.put(status):
                self._record_client_queue_depth(client)

    def _record_client_queue_depth(self, client: LiveAisClient) -> None:
        self._metrics = replace(
            self._metrics,
            client_queue_high_water=max(self._metrics.client_queue_high_water, client.queue_depth),
        )

    def _disconnect_slow_client(self, client: LiveAisClient) -> None:
        self._clients.discard(client)
        client.close("slow_client")
        self._metrics = replace(
            self._metrics,
            clients_connected=len(self._clients),
            slow_clients_disconnected=self._metrics.slow_clients_disconnected + 1,
        )

    def _snapshot_factory(self, *, truncated: bool) -> EventFactory:
        def factory(epoch: UUID, sequence: int, emitted_at: datetime) -> LiveAisServerEvent:
            positions, limited = self._snapshot_positions()
            return LiveAisSnapshotEvent(
                event="vessel.snapshot",
                stream_epoch=epoch,
                sequence=sequence,
                emitted_at=emitted_at,
                availability=self._availability,
                source_state=self._source_state,
                cache_age_seconds=None,
                coverage=self._coverage(emitted_at),
                positions=positions,
                truncated=truncated or limited or self._state_incomplete,
            )

        return factory

    def _position_factory(self, position: LiveAisPosition) -> EventFactory:
        def factory(epoch: UUID, sequence: int, emitted_at: datetime) -> LiveAisServerEvent:
            return LiveAisPositionEvent(
                event="vessel.position",
                stream_epoch=epoch,
                sequence=sequence,
                emitted_at=emitted_at,
                position=position,
            )

        return factory

    def _status_factory(self) -> EventFactory:
        def factory(epoch: UUID, sequence: int, emitted_at: datetime) -> LiveAisServerEvent:
            return LiveAisStatusEvent(
                event="stream.status",
                stream_epoch=epoch,
                sequence=sequence,
                emitted_at=emitted_at,
                connection_state=self._connection_state,
                source_state=self._source_state,
                cache_age_seconds=None,
                availability=self._availability,
                coverage=self._coverage(emitted_at),
                last_observation_at=self._last_observation_at,
                retry_at=None,
                detail=self._detail,
            )

        return factory

    def _gap_factory(self, reason: str, dropped_updates: int | None, detail: str) -> EventFactory:
        if reason not in {
            "provider_disconnect",
            "server_backpressure",
            "client_backpressure",
            "subscription_change",
        }:
            raise ValueError("unsupported public gap reason")

        def factory(epoch: UUID, sequence: int, emitted_at: datetime) -> LiveAisServerEvent:
            return LiveAisGapEvent(
                event="stream.gap",
                stream_epoch=epoch,
                sequence=sequence,
                emitted_at=emitted_at,
                gap_started_at=emitted_at,
                gap_ended_at=None,
                reason=reason,  # type: ignore[arg-type]
                dropped_updates=dropped_updates,
                replay_available=False,
                detail=detail,
            )

        return factory

    def _snapshot_positions(self) -> tuple[tuple[LiveAisPosition, ...], bool]:
        self._expire_positions()
        if self._availability == "DATA UNAVAILABLE" or self._coverage_state == "NO COVERAGE":
            return (), False
        ordered = sorted(
            (stored.position for stored in self._latest.values()),
            key=lambda position: (position.observed_at, position.mmsi),
            reverse=True,
        )
        limited = len(ordered) > self._config.snapshot_capacity
        return tuple(ordered[: self._config.snapshot_capacity]), limited

    def _coverage(self, effective_at: datetime) -> LiveAisCoverage:
        if self._coverage_state == "NO COVERAGE":
            return LiveAisCoverage(
                state="NO COVERAGE",
                description=NO_COVERAGE_DESCRIPTION,
                bounds=None,
                effective_at=effective_at,
            )
        return LiveAisCoverage(
            state="COVERED",
            description=GULF_COVERAGE_DESCRIPTION,
            bounds=LiveAisBounds(**PELYR_BOUNDS),
            effective_at=self._coverage_effective_at,
        )

    def _expire_positions(self, now_monotonic: float | None = None) -> None:
        current = self._monotonic() if now_monotonic is None else now_monotonic
        expired = tuple(
            mmsi
            for mmsi, stored in self._latest.items()
            if current - stored.received_at >= self._config.latest_ttl_seconds
        )
        for mmsi in expired:
            del self._latest[mmsi]
        if expired:
            self._metrics = replace(
                self._metrics,
                expired_positions=self._metrics.expired_positions + len(expired),
            )

    def _next_timeout(self) -> float:
        if self._pending_since is None:
            return self._config.maintenance_seconds
        remaining = self._config.coalesce_seconds - (self._monotonic() - self._pending_since)
        return max(0.001, min(self._config.maintenance_seconds, remaining))

    def _coalesce_due(self) -> bool:
        return self._pending_since is not None and (
            self._monotonic() - self._pending_since >= self._config.coalesce_seconds
        )

    def _utc_now(self) -> datetime:
        value = self._now()
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("gateway clock must be timezone-aware")
        return value.astimezone(UTC)


def _status_detail(reason: str) -> str:
    details = {
        "startup": "Live AIS worker is connecting.",
        "welcome_accepted": "Validated provider stream is available for the fixed pilot box.",
        "provider_rejected": "Provider rejected the bounded stream request.",
        "malformed_control_frame": "Provider control validation failed.",
        "source_directory_invalid": "Provider source attribution is unavailable.",
        "licence_invalid": "Provider source licence validation failed.",
        "heartbeat_timeout": "Provider heartbeat timed out.",
        "feed_loss": "Provider reported stream loss.",
        "socket_closed": "Provider connection closed.",
        "backoff_wait": "Live AIS worker is waiting before a bounded reconnect.",
        "shutdown": "Live AIS worker stopped cleanly.",
    }
    return details.get(reason, "Live AIS status changed.")
