import asyncio
import copy
import json
from collections import deque
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

import oceanscope_api.live_ais.worker as worker_module
from oceanscope_api.api.contracts.live_ais import LiveAisPosition
from oceanscope_api.live_ais import (
    PELYR_BOUNDS,
    PELYR_SUBSCRIPTION,
    PelyrProtocolError,
    PelyrSourceDirectoryError,
    PelyrWorker,
    PelyrWorkerConfig,
    PelyrWorkerConfigurationError,
    PelyrWorkerGapEvent,
    PelyrWorkerStatusEvent,
    parse_heartbeat,
    validate_subscription_confirmation,
    validate_welcome,
)

TEST_API_KEY = "TEST_DATA_not-a-real-pelyr-key"
NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)


def welcome_frame() -> dict[str, object]:
    # TEST DATA: fictional control metadata; never captured from a provider connection.
    return {
        "type": "welcome",
        "protocol": "pelyr.v1",
        "server_time": "2026-09-23T12:00:00Z",
        "subscribe_deadline_ms": 5000,
        "bbox_fields": ["west", "south", "east", "north"],
        "key": {"prefix": "test_", "scope": "collector_receiver"},
        "limits": {
            "subscriptions": 4,
            "bbox_per_subscription": 50,
            "bbox_per_connection": 80,
            "mmsi_per_subscription": 500,
            "output_bytes_per_second": 0,
            "quota_bytes_per_month": 0,
            "quota_bytes_used": 0,
        },
        "sources": [
            {"id": "0", "license": "NOASSERTION", "attribution": ""},
            {
                "id": "100",
                "license": "CC-BY-4.0",
                "attribution": "TEST DATA attribution for fictional source",
            },
        ],
    }


def subscribed_frame() -> dict[str, object]:
    # TEST DATA: fictional confirmation of the fixed subscription.
    return {
        "type": "subscribed",
        "id": "oceanscope-gulf-of-finland",
        "effective": {
            "bbox": [dict(PELYR_BOUNDS)],
            "fields": "position",
            "mmsi_count": 0,
        },
    }


def position_frame(*, license_id: object = "100") -> dict[str, object]:
    # TEST DATA: fictional vessel observation; never captured from Pelyr.
    return {
        "type": "position",
        "id": "test-position-001",
        "license": license_id,
        "data": {
            "mmsi": 230000001,
            "msg_type": 1,
            "lat": 60.17,
            "lon": 24.94,
            "sog": 12.5,
            "cog": 91.25,
            "heading": 90,
            "rx_ts": "2026-09-23T11:59:59Z",
        },
    }


def heartbeat_frame(**changes: object) -> dict[str, object]:
    frame: dict[str, object] = {
        "type": "heartbeat",
        "at": "2026-09-23T12:00:20Z",
        "sent": 12,
        "dropped": 0,
        "lag_ms": 112,
        "feed": "ok",
    }
    frame.update(changes)
    return frame


class FakeConnection:
    def __init__(self, frames: list[object]) -> None:
        self.frames = deque(frames)
        self.sent: list[str] = []
        self.closed = False
        self.close_code: int | None = None
        self.close_reason: str | None = None
        self._blocked = asyncio.Event()

    async def recv(self) -> str | bytes:
        if not self.frames:
            await self._blocked.wait()
            raise RuntimeError("fake connection released without a frame")
        item = self.frames.popleft()
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, (str, bytes)):
            return item
        return json.dumps(item)

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason
        self._blocked.set()


class FakeConnector:
    def __init__(self, outcomes: list[FakeConnection | BaseException]) -> None:
        self.outcomes = deque(outcomes)
        self.calls = 0
        self.in_flight = 0
        self.max_in_flight = 0
        self.last_key_repr = ""

    async def __call__(
        self,
        *,
        api_key: SecretStr,
        open_timeout: float,
        close_timeout: float,
    ) -> FakeConnection:
        del open_timeout, close_timeout
        self.calls += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.last_key_repr = repr(api_key)
        try:
            outcome = self.outcomes.popleft()
            if isinstance(outcome, BaseException):
                raise outcome
            return outcome
        finally:
            self.in_flight -= 1


async def wait_until(predicate: Callable[[], bool], *, attempts: int = 200) -> None:
    for _ in range(attempts):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition was not reached")


async def cancel_worker(task: asyncio.Task[None]) -> None:
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def worker_for(
    connection: FakeConnection,
    *,
    config: PelyrWorkerConfig | None = None,
    positions: list[LiveAisPosition] | None = None,
    statuses: list[PelyrWorkerStatusEvent] | None = None,
    gaps: list[PelyrWorkerGapEvent] | None = None,
    sleep: Callable[[float], Awaitable[None]] | None = None,
) -> tuple[PelyrWorker, FakeConnector]:
    connector = FakeConnector([connection])
    worker = PelyrWorker(
        api_key=SecretStr(TEST_API_KEY),
        connector=connector,
        config=config,
        position_sink=(positions if positions is not None else []).append,
        status_sink=(statuses if statuses is not None else []).append,
        gap_sink=(gaps if gaps is not None else []).append,
        now=lambda: NOW,
        sleep=sleep,
        jitter=lambda delay: delay,
        epoch_factory=lambda: "test-epoch",
    )
    return worker, connector


def test_validates_welcome_and_builds_connection_scoped_source_directory() -> None:
    welcome = validate_welcome(welcome_frame())

    assert welcome.subscription_deadline_seconds == 5
    assert welcome.source_directory.resolve("100").attribution_text.startswith("TEST DATA")


def test_accepts_zero_as_an_unlimited_runtime_limit() -> None:
    frame = welcome_frame()
    limits = frame["limits"]
    assert isinstance(limits, dict)
    limits["subscriptions"] = 0
    limits["bbox_per_subscription"] = 0
    limits["bbox_per_connection"] = 0

    validate_welcome(frame)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda frame: frame.update(protocol="pelyr.v0"),
        lambda frame: frame.update(subscribe_deadline_ms=0),
        lambda frame: frame.update(bbox_fields=["south", "west", "east", "north"]),
        lambda frame: frame.update(key={"scope": "browser"}),
        lambda frame: frame.update(sources=[]),
    ],
)
def test_rejects_invalid_welcome_control_data(
    mutate: Callable[[dict[str, object]], None],
) -> None:
    frame = welcome_frame()
    mutate(frame)

    with pytest.raises(PelyrProtocolError):
        validate_welcome(frame)


@pytest.mark.parametrize(
    "sources",
    [
        [
            {"id": 100, "license": "CC-BY-4.0", "attribution": "TEST DATA"},
            {"id": 100, "license": "CC-BY-4.0", "attribution": "TEST DATA"},
        ],
        [{"id": 100, "license": "NOASSERTION", "attribution": "TEST DATA"}],
        [{"id": 100, "license": "CC-BY-4.0", "attribution": ""}],
        [{"id": 0, "license": "CC-BY-4.0", "attribution": "TEST DATA"}],
    ],
)
def test_rejects_unsafe_welcome_source_directory(sources: list[dict[str, object]]) -> None:
    frame = welcome_frame()
    frame["sources"] = sources

    with pytest.raises(PelyrSourceDirectoryError):
        validate_welcome(frame)


def test_requires_exact_fixed_subscription_confirmation() -> None:
    validate_subscription_confirmation(subscribed_frame())

    changed = subscribed_frame()
    effective = changed["effective"]
    assert isinstance(effective, dict)
    effective["bbox"] = [{**PELYR_BOUNDS, "east": 27.0}]
    with pytest.raises(PelyrProtocolError):
        validate_subscription_confirmation(changed)


def test_rejects_provider_subscription_error_without_copying_detail() -> None:
    frame = {"type": "error", "code": "test", "detail": "raw provider detail"}

    with pytest.raises(Exception) as error:
        validate_subscription_confirmation(frame)

    assert "raw provider detail" not in str(error.value)


@pytest.mark.parametrize("lag_ms", [float("nan"), float("inf"), -1])
def test_rejects_non_finite_or_negative_heartbeat_metrics(lag_ms: float) -> None:
    with pytest.raises(PelyrProtocolError):
        parse_heartbeat(heartbeat_frame(lag_ms=lag_ms))


def test_connects_with_fixed_subscription_and_normalizes_through_b5() -> None:
    async def scenario() -> None:
        connection = FakeConnection([welcome_frame(), subscribed_frame(), position_frame()])
        positions: list[LiveAisPosition] = []
        statuses: list[PelyrWorkerStatusEvent] = []
        gaps: list[PelyrWorkerGapEvent] = []
        worker, connector = worker_for(
            connection,
            positions=positions,
            statuses=statuses,
            gaps=gaps,
        )

        task = asyncio.create_task(worker.run())
        await wait_until(lambda: len(positions) == 1)

        sent = json.loads(connection.sent[0])
        assert sent == PELYR_SUBSCRIPTION
        assert connector.calls == 1
        assert connector.max_in_flight == 1
        assert connector.last_key_repr == "SecretStr('**********')"
        position = positions[0]
        assert position.mmsi == "230000001"
        assert position.provenance.attribution_text.startswith("TEST DATA")
        assert any(status.connection_state == "CONNECTED" for status in statuses)

        await cancel_worker(task)
        assert connection.closed is True
        assert gaps[-1].reason == "shutdown"
        assert gaps[-1].replay_available is False
        assert statuses[-1].connection_state == "DISCONNECTED"

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("frame", "reason"),
    [
        (heartbeat_frame(feed="stalled"), "feed_loss"),
        (heartbeat_frame(dropped=1), "feed_loss"),
        ({"type": "error", "code": "test-rejection"}, "provider_rejected"),
        ("not-json", "malformed_control_frame"),
        (position_frame(license_id=999), "licence_invalid"),
    ],
)
def test_continuity_failures_emit_non_replayable_gap(frame: object, reason: str) -> None:
    async def scenario() -> None:
        connection = FakeConnection([welcome_frame(), subscribed_frame(), frame])
        gaps: list[PelyrWorkerGapEvent] = []
        statuses: list[PelyrWorkerStatusEvent] = []
        sleep_started = asyncio.Event()

        async def blocked_sleep(_: float) -> None:
            sleep_started.set()
            await asyncio.Event().wait()

        worker, _ = worker_for(
            connection,
            gaps=gaps,
            statuses=statuses,
            sleep=blocked_sleep,
        )
        task = asyncio.create_task(worker.run())
        await asyncio.wait_for(sleep_started.wait(), timeout=1)

        assert gaps[0].reason == reason
        assert gaps[0].replay_available is False
        failure_statuses = [status for status in statuses if status.reason == reason]
        assert failure_statuses[-1].availability == "DATA UNAVAILABLE"
        assert failure_statuses[-1].freshness == "OFFLINE"

        await cancel_worker(task)

    asyncio.run(scenario())


def test_heartbeat_timeout_is_not_inferred_from_position_silence() -> None:
    async def scenario() -> None:
        connection = FakeConnection([welcome_frame(), subscribed_frame()])
        gaps: list[PelyrWorkerGapEvent] = []
        sleep_started = asyncio.Event()

        async def blocked_sleep(_: float) -> None:
            sleep_started.set()
            await asyncio.Event().wait()

        worker, _ = worker_for(
            connection,
            config=PelyrWorkerConfig(heartbeat_timeout_seconds=0.01),
            gaps=gaps,
            sleep=blocked_sleep,
        )
        task = asyncio.create_task(worker.run())
        await asyncio.wait_for(sleep_started.wait(), timeout=1)

        assert gaps[0].reason == "heartbeat_timeout"
        await cancel_worker(task)

    asyncio.run(scenario())


def test_retry_backoff_is_capped_and_connection_attempts_are_serial() -> None:
    async def scenario() -> None:
        connector = FakeConnector([OSError("TEST DATA failure") for _ in range(7)])
        sleeps: list[float] = []

        async def record_sleep(delay: float) -> None:
            sleeps.append(delay)
            if len(sleeps) == 7:
                raise asyncio.CancelledError

        worker = PelyrWorker(
            api_key=SecretStr(TEST_API_KEY),
            connector=connector,
            sleep=record_sleep,
            jitter=lambda delay: delay,
            now=lambda: NOW,
        )

        with pytest.raises(asyncio.CancelledError):
            await worker.run()

        assert sleeps == [1, 2, 4, 8, 16, 30, 30]
        assert connector.calls == 7
        assert connector.max_in_flight == 1

    asyncio.run(scenario())


def test_connection_attempt_has_an_explicit_timeout() -> None:
    async def scenario() -> None:
        statuses: list[PelyrWorkerStatusEvent] = []
        sleep_started = asyncio.Event()

        async def blocked_connector(
            *,
            api_key: SecretStr,
            open_timeout: float,
            close_timeout: float,
        ) -> FakeConnection:
            del api_key, open_timeout, close_timeout
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

        async def blocked_sleep(_: float) -> None:
            sleep_started.set()
            await asyncio.Event().wait()

        worker = PelyrWorker(
            api_key=SecretStr(TEST_API_KEY),
            connector=blocked_connector,
            config=PelyrWorkerConfig(connect_timeout_seconds=0.01),
            status_sink=statuses.append,
            sleep=blocked_sleep,
            jitter=lambda delay: delay,
            now=lambda: NOW,
        )
        task = asyncio.create_task(worker.run())
        await asyncio.wait_for(sleep_started.wait(), timeout=1)

        assert any(status.reason == "socket_closed" for status in statuses)
        await cancel_worker(task)

    asyncio.run(scenario())


def test_second_run_is_rejected_and_cancellation_leaves_no_background_task() -> None:
    async def scenario() -> None:
        connection = FakeConnection([welcome_frame(), subscribed_frame()])
        statuses: list[PelyrWorkerStatusEvent] = []
        worker, _ = worker_for(connection, statuses=statuses)
        first = asyncio.create_task(worker.run())
        await wait_until(lambda: any(status.connection_state == "CONNECTED" for status in statuses))

        with pytest.raises(RuntimeError, match="already running"):
            await worker.run()

        await cancel_worker(first)
        assert first.done()
        assert connection.closed is True

    asyncio.run(scenario())


def test_key_raw_frames_and_positions_do_not_leak_into_status_or_gap_events() -> None:
    async def scenario() -> None:
        raw_marker = "RAW_PROVIDER_MARKER"
        connection = FakeConnection(
            [welcome_frame(), subscribed_frame(), f'{{"type":"unknown","x":"{raw_marker}"}}']
        )
        statuses: list[PelyrWorkerStatusEvent] = []
        gaps: list[PelyrWorkerGapEvent] = []
        sleep_started = asyncio.Event()

        async def blocked_sleep(_: float) -> None:
            sleep_started.set()
            await asyncio.Event().wait()

        worker, _ = worker_for(
            connection,
            statuses=statuses,
            gaps=gaps,
            sleep=blocked_sleep,
        )
        task = asyncio.create_task(worker.run())
        await asyncio.wait_for(sleep_started.wait(), timeout=1)

        serialized = repr(statuses) + repr(gaps) + repr(worker)
        assert TEST_API_KEY not in serialized
        assert raw_marker not in serialized
        assert "230000001" not in serialized
        assert "24.94" not in serialized
        assert all(status.availability == "DATA UNAVAILABLE" for status in statuses[-2:])

        await cancel_worker(task)

    asyncio.run(scenario())


def test_concrete_connector_keeps_key_out_of_url_and_disables_transport_logging(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def scenario() -> None:
        captured: dict[str, object] = {}
        connection = FakeConnection([])

        async def fake_connect(uri: str, **kwargs: object) -> FakeConnection:
            captured["uri"] = uri
            captured.update(kwargs)
            return connection

        monkeypatch.setattr(worker_module, "connect", fake_connect)
        result = await worker_module.open_pelyr_connection(
            api_key=SecretStr(TEST_API_KEY),
            open_timeout=10,
            close_timeout=5,
        )

        assert result is connection
        assert TEST_API_KEY not in str(captured["uri"])
        assert captured["additional_headers"] == {"Authorization": f"Bearer {TEST_API_KEY}"}
        logger = captured["logger"]
        assert isinstance(logger, worker_module.logging.Logger)
        assert logger.isEnabledFor(worker_module.logging.CRITICAL) is False

    asyncio.run(scenario())


def test_environment_factory_requires_only_the_server_side_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PELYR_API_KEY", raising=False)
    with pytest.raises(PelyrWorkerConfigurationError, match="PELYR_API_KEY"):
        PelyrWorker.from_environment()

    monkeypatch.setenv("PELYR_API_KEY", TEST_API_KEY)
    worker = PelyrWorker.from_environment()
    assert TEST_API_KEY not in repr(worker)


def test_worker_configuration_rejects_unbounded_retry_values() -> None:
    with pytest.raises(PelyrWorkerConfigurationError, match="capped"):
        PelyrWorkerConfig(backoff_seconds=(1, 31))


def test_test_helpers_do_not_mutate_shared_control_fixtures() -> None:
    original = welcome_frame()
    changed = copy.deepcopy(original)
    sources = changed["sources"]
    assert isinstance(sources, list)
    sources.clear()

    assert welcome_frame() == original
