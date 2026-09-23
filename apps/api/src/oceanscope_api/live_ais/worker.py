"""Bounded supervision for the single Pelyr Live AIS connection.

The worker owns only the upstream connection and its continuity semantics. It has no
public route, persistence, replay, client fan-out, or dynamic subscription surface.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import os
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Final, Literal, Protocol
from uuid import uuid4

from pydantic import SecretStr
from websockets.asyncio.client import connect

from oceanscope_api.api.contracts.live_ais import LiveAisPosition
from oceanscope_api.live_ais.pelyr import (
    PELYR_STREAM_URL,
    PelyrNormalizationError,
    PelyrPositionNormalizer,
    PelyrSourceDescriptor,
    PelyrSourceDirectory,
)

PELYR_PROTOCOL: Final = "pelyr.v1"
PELYR_API_KEY_ENV: Final = "PELYR_API_KEY"
PELYR_SUBSCRIPTION_ID: Final = "oceanscope-gulf-of-finland"
PELYR_BOUNDS: Final = {
    "west": 23.50,
    "south": 59.50,
    "east": 26.50,
    "north": 60.50,
}
PELYR_SUBSCRIPTION: Final = {
    "type": "subscribe",
    "id": PELYR_SUBSCRIPTION_ID,
    "bbox": [PELYR_BOUNDS],
    "fields": "position",
}
_TRANSPORT_LOGGER: Final = logging.Logger(
    "oceanscope.live_ais.pelyr.transport", level=logging.CRITICAL + 1
)

ConnectionState = Literal["CONNECTING", "CONNECTED", "RECONNECTING", "DISCONNECTED"]
WorkerFreshness = Literal["LIVE", "DELAYED", "OFFLINE"]
WorkerAvailability = Literal["AVAILABLE", "DATA UNAVAILABLE"]
WorkerReason = Literal[
    "startup",
    "welcome_accepted",
    "provider_rejected",
    "malformed_control_frame",
    "source_directory_invalid",
    "licence_invalid",
    "heartbeat_timeout",
    "feed_loss",
    "socket_closed",
    "backoff_wait",
    "shutdown",
]


class PelyrWorkerConfigurationError(ValueError):
    """Raised when the bounded worker cannot be configured safely."""


class PelyrProtocolError(ValueError):
    """Raised for an invalid provider control frame without retaining that frame."""


class PelyrSourceDirectoryError(PelyrProtocolError):
    """Raised when ``welcome.sources`` is unsafe or structurally invalid."""


class PelyrConnection(Protocol):
    """Small transport boundary used by the worker and mocked by tests."""

    async def recv(self) -> str | bytes: ...

    async def send(self, message: str) -> None: ...

    async def close(self, code: int = 1000, reason: str = "") -> None: ...


class PelyrConnector(Protocol):
    def __call__(
        self,
        *,
        api_key: SecretStr,
        open_timeout: float,
        close_timeout: float,
    ) -> Awaitable[PelyrConnection]: ...


@dataclass(frozen=True, slots=True)
class PelyrWorkerConfig:
    """Fixed operational limits; subscription geography is intentionally not configurable."""

    connect_timeout_seconds: float = 10.0
    welcome_timeout_seconds: float = 5.0
    subscription_send_timeout_seconds: float = 5.0
    subscription_confirmation_timeout_seconds: float = 5.0
    heartbeat_timeout_seconds: float = 45.0
    close_timeout_seconds: float = 5.0
    stable_connection_seconds: float = 60.0
    backoff_seconds: tuple[float, ...] = (1.0, 2.0, 4.0, 8.0, 16.0, 30.0)
    jitter_ratio: float = 0.20

    def __post_init__(self) -> None:
        durations = (
            self.connect_timeout_seconds,
            self.welcome_timeout_seconds,
            self.subscription_send_timeout_seconds,
            self.subscription_confirmation_timeout_seconds,
            self.heartbeat_timeout_seconds,
            self.close_timeout_seconds,
            self.stable_connection_seconds,
        )
        if any(not math.isfinite(value) or value <= 0 for value in durations):
            raise PelyrWorkerConfigurationError("worker timeouts must be positive finite values")
        if not self.backoff_seconds or any(
            not math.isfinite(value) or value <= 0 or value > 30 for value in self.backoff_seconds
        ):
            raise PelyrWorkerConfigurationError(
                "backoff delays must be positive finite values capped at 30 seconds"
            )
        if not math.isfinite(self.jitter_ratio) or not 0 <= self.jitter_ratio <= 0.20:
            raise PelyrWorkerConfigurationError("jitter_ratio must be between 0 and 0.20")


@dataclass(frozen=True, slots=True)
class PelyrWorkerMetrics:
    """Bounded-cardinality counters without vessel, position, frame, or key data."""

    connection_attempts: int = 0
    reconnects: int = 0
    frames_received: int = 0
    positions_accepted: int = 0
    frames_rejected: int = 0
    heartbeats_received: int = 0
    provider_sent: int = 0
    provider_dropped: int = 0
    provider_lag_ms: float | None = None

    def __post_init__(self) -> None:
        integer_values = (
            self.connection_attempts,
            self.reconnects,
            self.frames_received,
            self.positions_accepted,
            self.frames_rejected,
            self.heartbeats_received,
            self.provider_sent,
            self.provider_dropped,
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in integer_values
        ):
            raise ValueError("worker counters must be non-negative integers")
        if self.provider_lag_ms is not None and (
            not math.isfinite(self.provider_lag_ms) or self.provider_lag_ms < 0
        ):
            raise ValueError("provider_lag_ms must be a non-negative finite number")


@dataclass(frozen=True, slots=True)
class PelyrWorkerStatusEvent:
    event: Literal["worker.status"]
    occurred_at: datetime
    connection_state: ConnectionState
    freshness: WorkerFreshness
    availability: WorkerAvailability
    reason: WorkerReason
    reconnect_attempt: int
    stream_epoch: str | None
    replay_available: Literal[False]
    metrics: PelyrWorkerMetrics

    def __post_init__(self) -> None:
        _require_utc(self.occurred_at, "occurred_at")
        if self.reconnect_attempt < 0:
            raise ValueError("reconnect_attempt must be non-negative")
        if self.stream_epoch is not None and not self.stream_epoch.strip():
            raise ValueError("stream_epoch must be opaque non-empty text")


@dataclass(frozen=True, slots=True)
class PelyrWorkerGapEvent:
    event: Literal["stream.gap"]
    occurred_at: datetime
    stream_epoch: str
    reason: WorkerReason
    replay_available: Literal[False]
    metrics: PelyrWorkerMetrics

    def __post_init__(self) -> None:
        _require_utc(self.occurred_at, "occurred_at")
        if not self.stream_epoch.strip():
            raise ValueError("stream_epoch must be opaque non-empty text")


@dataclass(frozen=True, slots=True)
class PelyrWelcome:
    subscription_deadline_seconds: float
    source_directory: PelyrSourceDirectory


@dataclass(frozen=True, slots=True)
class PelyrHeartbeat:
    sent: int
    dropped: int
    lag_ms: float
    feed: str


class _WorkerRetry(Exception):
    def __init__(self, reason: WorkerReason) -> None:
        self.reason = reason
        super().__init__(reason)


async def open_pelyr_connection(
    *,
    api_key: SecretStr,
    open_timeout: float,
    close_timeout: float,
) -> PelyrConnection:
    """Open the one server-side Pelyr socket without placing the key in the URL."""

    return await connect(
        PELYR_STREAM_URL,
        additional_headers={
            "Authorization": f"Bearer {api_key.get_secret_value()}",
        },
        open_timeout=open_timeout,
        close_timeout=close_timeout,
        max_size=1_048_576,
        max_queue=16,
        logger=_TRANSPORT_LOGGER,
    )


def validate_welcome(frame: Mapping[str, object]) -> PelyrWelcome:
    """Validate the connection-scoped provider contract before subscribing."""

    if frame.get("type") != "welcome" or frame.get("protocol") != PELYR_PROTOCOL:
        raise PelyrProtocolError("invalid Pelyr welcome protocol")
    _provider_time(frame.get("server_time"), "server_time")

    deadline_ms = _nonnegative_int(frame.get("subscribe_deadline_ms"), "subscribe_deadline_ms")
    if deadline_ms == 0:
        raise PelyrProtocolError("subscribe_deadline_ms must be positive")

    bbox_fields = frame.get("bbox_fields")
    if bbox_fields != ["west", "south", "east", "north"]:
        raise PelyrProtocolError("welcome bbox_fields do not match the v1 contract")

    key = _mapping(frame.get("key"), "key")
    if key.get("scope") not in {"collector", "collector_receiver"}:
        raise PelyrProtocolError("welcome key scope is not supported")

    limits = _mapping(frame.get("limits"), "limits")
    for name in (
        "subscriptions",
        "bbox_per_subscription",
        "bbox_per_connection",
        "mmsi_per_subscription",
        "output_bytes_per_second",
        "quota_bytes_per_month",
        "quota_bytes_used",
    ):
        _nonnegative_int(limits.get(name), name)
    raw_sources = frame.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise PelyrSourceDirectoryError("welcome sources must be a non-empty array")

    descriptors: list[PelyrSourceDescriptor] = []
    publishable = 0
    try:
        for raw_source in raw_sources:
            source = PelyrSourceDescriptor.from_provider_entry(_mapping(raw_source, "source entry"))
            if source.source_id == 0:
                if (
                    source.license_identifier.strip().upper() != "NOASSERTION"
                    or source.attribution_text.strip()
                ):
                    raise PelyrSourceDirectoryError(
                        "Pelyr source 0 must remain unpublishable NOASSERTION metadata"
                    )
            else:
                source.validate_publishable()
                publishable += 1
            descriptors.append(source)
        directory = PelyrSourceDirectory(descriptors)
    except PelyrSourceDirectoryError:
        raise
    except (PelyrNormalizationError, TypeError, ValueError) as error:
        raise PelyrSourceDirectoryError("welcome source directory is invalid") from error

    if publishable == 0:
        raise PelyrSourceDirectoryError("welcome has no publishable source")
    return PelyrWelcome(deadline_ms / 1000, directory)


def validate_subscription_confirmation(frame: Mapping[str, object]) -> None:
    """Require the provider's effective selection to equal the fixed request."""

    if frame.get("type") == "error":
        raise _WorkerRetry("provider_rejected")
    if frame.get("type") != "subscribed" or frame.get("id") != PELYR_SUBSCRIPTION_ID:
        raise PelyrProtocolError("invalid subscription confirmation")
    effective = _mapping(frame.get("effective"), "effective")
    if effective.get("fields") != "position" or effective.get("bbox") != [PELYR_BOUNDS]:
        raise PelyrProtocolError("provider effective subscription differs from the fixed request")
    _nonnegative_int(effective.get("mmsi_count"), "mmsi_count")
    notes = frame.get("notes", [])
    if not isinstance(notes, list) or any(not isinstance(note, str) for note in notes):
        raise PelyrProtocolError("subscription notes must be text")
    if notes:
        raise PelyrProtocolError("provider reported notes for the fixed subscription")


def parse_heartbeat(frame: Mapping[str, object]) -> PelyrHeartbeat:
    if frame.get("type") != "heartbeat":
        raise PelyrProtocolError("expected a heartbeat frame")
    _provider_time(frame.get("at"), "at")
    sent = _nonnegative_int(frame.get("sent"), "sent")
    dropped = _nonnegative_int(frame.get("dropped"), "dropped")
    lag_ms = _nonnegative_number(frame.get("lag_ms"), "lag_ms")
    feed = frame.get("feed")
    if not isinstance(feed, str) or not feed:
        raise PelyrProtocolError("heartbeat feed must be text")
    return PelyrHeartbeat(sent=sent, dropped=dropped, lag_ms=lag_ms, feed=feed)


class PelyrWorker:
    """Supervise one bounded Pelyr connection and emit normalized observations."""

    def __init__(
        self,
        *,
        api_key: SecretStr,
        connector: PelyrConnector = open_pelyr_connection,
        config: PelyrWorkerConfig | None = None,
        normalizer: PelyrPositionNormalizer | None = None,
        position_sink: Callable[[LiveAisPosition], None] | None = None,
        status_sink: Callable[[PelyrWorkerStatusEvent], None] | None = None,
        gap_sink: Callable[[PelyrWorkerGapEvent], None] | None = None,
        now: Callable[[], datetime] | None = None,
        monotonic: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        jitter: Callable[[float], float] | None = None,
        epoch_factory: Callable[[], str] | None = None,
    ) -> None:
        if not api_key.get_secret_value().strip():
            raise PelyrWorkerConfigurationError("PELYR_API_KEY must be non-empty")
        self._api_key = api_key
        self._connector = connector
        self._config = config or PelyrWorkerConfig()
        self._normalizer = normalizer or PelyrPositionNormalizer()
        self._position_sink = position_sink or _ignore
        self._status_sink = status_sink or _ignore
        self._gap_sink = gap_sink or _ignore
        self._now = now or (lambda: datetime.now(UTC))
        self._monotonic = monotonic or time.monotonic
        self._sleep = sleep or asyncio.sleep
        self._jitter = jitter or self._bounded_jitter
        self._epoch_factory = epoch_factory or (lambda: str(uuid4()))
        self._metrics = PelyrWorkerMetrics()
        self._active_connection: PelyrConnection | None = None
        self._stream_epoch: str | None = None
        self._connected_at: float | None = None
        self._running = False

    @classmethod
    def from_environment(cls, **kwargs: object) -> PelyrWorker:
        raw_key = os.environ.get(PELYR_API_KEY_ENV)
        if raw_key is None or not raw_key.strip():
            raise PelyrWorkerConfigurationError("PELYR_API_KEY is required")
        return cls(api_key=SecretStr(raw_key), **kwargs)  # type: ignore[arg-type]

    @property
    def metrics(self) -> PelyrWorkerMetrics:
        return self._metrics

    async def run(self) -> None:
        """Run until cancelled; cancellation is propagated after a clean shutdown."""

        if self._running:
            raise RuntimeError("Pelyr worker is already running")
        self._running = True
        reconnect_attempt = 0
        self._emit_status("CONNECTING", "OFFLINE", "DATA UNAVAILABLE", "startup", 0)
        try:
            while True:
                self._metrics = replace(
                    self._metrics,
                    connection_attempts=self._metrics.connection_attempts + 1,
                )
                failure_reason: WorkerReason
                try:
                    await self._run_connection(reconnect_attempt)
                    failure_reason = "socket_closed"
                except asyncio.CancelledError:
                    raise
                except _WorkerRetry as error:
                    failure_reason = error.reason
                except PelyrSourceDirectoryError:
                    failure_reason = "source_directory_invalid"
                except PelyrProtocolError:
                    failure_reason = "malformed_control_frame"
                except Exception:
                    failure_reason = "socket_closed"
                finally:
                    await self._close_active_connection()

                if (
                    self._connected_at is not None
                    and self._monotonic() - self._connected_at
                    >= self._config.stable_connection_seconds
                ):
                    reconnect_attempt = 0
                reconnect_attempt += 1
                self._metrics = replace(
                    self._metrics,
                    reconnects=self._metrics.reconnects + 1,
                )
                if self._stream_epoch is not None:
                    self._gap_sink(
                        PelyrWorkerGapEvent(
                            event="stream.gap",
                            occurred_at=self._utc_now(),
                            stream_epoch=self._stream_epoch,
                            reason=failure_reason,
                            replay_available=False,
                            metrics=self._metrics,
                        )
                    )
                self._emit_status(
                    "RECONNECTING",
                    "OFFLINE",
                    "DATA UNAVAILABLE",
                    failure_reason,
                    reconnect_attempt,
                )
                self._stream_epoch = None
                self._connected_at = None

                base_delay = self._config.backoff_seconds[
                    min(reconnect_attempt - 1, len(self._config.backoff_seconds) - 1)
                ]
                delay = self._jitter(base_delay)
                if not math.isfinite(delay) or not 0 <= delay <= 30:
                    raise PelyrWorkerConfigurationError(
                        "jitter must return a finite delay between 0 and 30 seconds"
                    )
                self._emit_status(
                    "RECONNECTING",
                    "OFFLINE",
                    "DATA UNAVAILABLE",
                    "backoff_wait",
                    reconnect_attempt,
                )
                await self._sleep(delay)
                self._emit_status(
                    "CONNECTING",
                    "OFFLINE",
                    "DATA UNAVAILABLE",
                    "startup",
                    reconnect_attempt,
                )
        finally:
            await self._close_active_connection()
            if self._stream_epoch is not None:
                self._gap_sink(
                    PelyrWorkerGapEvent(
                        event="stream.gap",
                        occurred_at=self._utc_now(),
                        stream_epoch=self._stream_epoch,
                        reason="shutdown",
                        replay_available=False,
                        metrics=self._metrics,
                    )
                )
            self._stream_epoch = None
            self._connected_at = None
            self._emit_status(
                "DISCONNECTED",
                "OFFLINE",
                "DATA UNAVAILABLE",
                "shutdown",
                reconnect_attempt,
            )
            self._running = False

    async def _run_connection(self, reconnect_attempt: int) -> None:
        try:
            async with asyncio.timeout(self._config.connect_timeout_seconds):
                connection = await self._connector(
                    api_key=self._api_key,
                    open_timeout=self._config.connect_timeout_seconds,
                    close_timeout=self._config.close_timeout_seconds,
                )
        except TimeoutError as error:
            raise _WorkerRetry("socket_closed") from error
        self._active_connection = connection

        welcome_frame = await self._receive_control(
            connection, self._config.welcome_timeout_seconds
        )
        try:
            welcome = validate_welcome(welcome_frame)
        except PelyrSourceDirectoryError:
            raise
        except PelyrProtocolError:
            raise
        self._stream_epoch = self._epoch_factory()

        deadline = min(
            welcome.subscription_deadline_seconds,
            self._config.subscription_send_timeout_seconds,
        )
        try:
            async with asyncio.timeout(deadline):
                await connection.send(json.dumps(PELYR_SUBSCRIPTION, separators=(",", ":")))
        except TimeoutError as error:
            raise _WorkerRetry("provider_rejected") from error

        confirmation = await self._receive_control(
            connection, self._config.subscription_confirmation_timeout_seconds
        )
        validate_subscription_confirmation(confirmation)
        self._connected_at = self._monotonic()
        last_heartbeat = self._connected_at
        self._emit_status(
            "CONNECTED",
            "LIVE",
            "AVAILABLE",
            "welcome_accepted",
            reconnect_attempt,
        )

        while True:
            remaining = self._config.heartbeat_timeout_seconds - (
                self._monotonic() - last_heartbeat
            )
            if remaining <= 0:
                raise _WorkerRetry("heartbeat_timeout")
            try:
                frame = await self._receive_control(connection, remaining)
            except TimeoutError as error:
                raise _WorkerRetry("heartbeat_timeout") from error
            frame_type = frame.get("type")
            if frame_type == "heartbeat":
                heartbeat = parse_heartbeat(frame)
                self._metrics = replace(
                    self._metrics,
                    heartbeats_received=self._metrics.heartbeats_received + 1,
                    provider_sent=heartbeat.sent,
                    provider_dropped=heartbeat.dropped,
                    provider_lag_ms=heartbeat.lag_ms,
                )
                last_heartbeat = self._monotonic()
                if heartbeat.feed == "stalled" or heartbeat.dropped > 0:
                    raise _WorkerRetry("feed_loss")
                continue
            if frame_type == "position":
                try:
                    welcome.source_directory.resolve(frame.get("license"))
                except PelyrNormalizationError as error:
                    self._reject_frame()
                    raise _WorkerRetry("licence_invalid") from error
                ingested_at = self._utc_now()
                try:
                    position = self._normalizer.normalize(
                        frame,
                        welcome.source_directory,
                        ingested_at=ingested_at,
                        normalized_at=self._utc_now(),
                    )
                except PelyrNormalizationError:
                    self._reject_frame()
                    continue
                self._metrics = replace(
                    self._metrics,
                    positions_accepted=self._metrics.positions_accepted + 1,
                )
                self._position_sink(position)
                continue
            if frame_type == "error":
                raise _WorkerRetry("provider_rejected")
            if frame_type == "notice":
                notice_code = frame.get("code")
                if notice_code in {"slow_consumer_warning", "throttled"}:
                    raise _WorkerRetry("feed_loss")
                if notice_code == "empty_subscription":
                    continue
            if frame_type == "pong":
                continue
            self._reject_frame()
            raise _WorkerRetry("malformed_control_frame")

    async def _receive_control(
        self, connection: PelyrConnection, timeout_seconds: float
    ) -> Mapping[str, object]:
        async with asyncio.timeout(timeout_seconds):
            raw_frame = await connection.recv()
        self._metrics = replace(
            self._metrics,
            frames_received=self._metrics.frames_received + 1,
        )
        if isinstance(raw_frame, bytes):
            try:
                raw_frame = raw_frame.decode("utf-8")
            except UnicodeDecodeError as error:
                raise PelyrProtocolError("provider frame is not UTF-8") from error
        try:
            parsed = json.loads(raw_frame)
        except (json.JSONDecodeError, TypeError) as error:
            raise PelyrProtocolError("provider frame is not valid JSON") from error
        if not isinstance(parsed, dict) or any(not isinstance(key, str) for key in parsed):
            raise PelyrProtocolError("provider control frame must be an object")
        return parsed

    async def _close_active_connection(self) -> None:
        connection = self._active_connection
        self._active_connection = None
        if connection is None:
            return
        try:
            async with asyncio.timeout(self._config.close_timeout_seconds):
                await connection.close(code=1000, reason="worker shutdown")
        except Exception:
            return

    def _reject_frame(self) -> None:
        self._metrics = replace(
            self._metrics,
            frames_rejected=self._metrics.frames_rejected + 1,
        )

    def _emit_status(
        self,
        connection_state: ConnectionState,
        freshness: WorkerFreshness,
        availability: WorkerAvailability,
        reason: WorkerReason,
        reconnect_attempt: int,
    ) -> None:
        self._status_sink(
            PelyrWorkerStatusEvent(
                event="worker.status",
                occurred_at=self._utc_now(),
                connection_state=connection_state,
                freshness=freshness,
                availability=availability,
                reason=reason,
                reconnect_attempt=reconnect_attempt,
                stream_epoch=self._stream_epoch,
                replay_available=False,
                metrics=self._metrics,
            )
        )

    def _bounded_jitter(self, base_delay: float) -> float:
        lower = max(0.0, base_delay * (1 - self._config.jitter_ratio))
        upper = min(30.0, base_delay * (1 + self._config.jitter_ratio))
        return random.uniform(lower, upper)

    def _utc_now(self) -> datetime:
        return _require_utc(self._now(), "worker clock")


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise PelyrProtocolError(f"{name} must be an object")
    return value


def _nonnegative_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PelyrProtocolError(f"{name} must be a non-negative integer")
    return value


def _nonnegative_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PelyrProtocolError(f"{name} must be a non-negative finite number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise PelyrProtocolError(f"{name} must be a non-negative finite number")
    return number


def _provider_time(value: object, name: str) -> datetime:
    if not isinstance(value, str):
        raise PelyrProtocolError(f"{name} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise PelyrProtocolError(f"{name} must be a valid timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PelyrProtocolError(f"{name} must be timezone-aware")
    return parsed.astimezone(UTC)


def _require_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    if value.utcoffset() != timedelta(0):
        raise ValueError(f"{name} must be UTC")
    return value.astimezone(UTC)


def _ignore(_: object) -> None:
    return None
