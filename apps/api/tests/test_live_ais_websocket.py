import asyncio
from collections.abc import MutableMapping
from contextlib import suppress
from datetime import UTC, datetime

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from starlette.websockets import WebSocketDisconnect

from oceanscope_api import main as main_module
from oceanscope_api.api.contracts.live_ais import LiveAisServerEvent
from oceanscope_api.api.routes.live_ais import LiveAisAccessPolicy, _serve_client
from oceanscope_api.core.settings import Settings
from oceanscope_api.live_ais.gateway import LiveAisGateway, LiveAisGatewayConfig
from oceanscope_api.live_ais.worker import PelyrWorkerMetrics, PelyrWorkerStatusEvent
from oceanscope_api.main import create_app


def make_settings(environment: str, origins: str) -> Settings:
    return Settings.model_validate(
        {
            "environment": environment,
            "live_ais_origins": origins,
            "PELYR_API_KEY": None,
        }
    )


def test_websocket_sends_unavailable_snapshot_first_without_key() -> None:
    settings = make_settings("test", "http://testserver")
    with (
        TestClient(create_app(settings=settings)) as client,
        client.websocket_connect(
            "/live-ais/ws", headers={"origin": "http://testserver"}
        ) as websocket,
    ):
        snapshot = websocket.receive_json()
        status = websocket.receive_json()

    assert snapshot["event"] == "vessel.snapshot"
    assert snapshot["sequence"] == 0
    assert snapshot["availability"] == "DATA UNAVAILABLE"
    assert snapshot["positions"] == []
    assert status["event"] == "stream.status"
    assert status["sequence"] == 1


def test_websocket_rejects_missing_and_unapproved_origins() -> None:
    settings = make_settings("test", "http://testserver")
    with TestClient(create_app(settings=settings)) as client:
        for headers in (
            {},
            {"origin": "null"},
            {"origin": "https://unapproved.example"},
        ):
            try:
                with client.websocket_connect("/live-ais/ws", headers=headers):
                    raise AssertionError("unapproved WebSocket must not be accepted")
            except WebSocketDisconnect as error:
                assert error.code == 1008


def test_development_is_limited_to_configured_loopback_origin() -> None:
    settings = make_settings("development", "https://product.example")
    with TestClient(create_app(settings=settings)) as client:
        try:
            with client.websocket_connect(
                "/live-ais/ws", headers={"origin": "https://product.example"}
            ):
                raise AssertionError("non-loopback development WebSocket must not be accepted")
        except WebSocketDisconnect as error:
            assert error.code == 1008


def test_development_rejects_forged_loopback_origin_from_remote_client() -> None:
    policy = LiveAisAccessPolicy(
        environment="development",
        allowed_origins=frozenset({"http://localhost:5173"}),
    )

    assert policy.rejection_reason("http://localhost:5173", "203.0.113.10") == "loopback_only"
    assert policy.rejection_reason("http://localhost:5173", "127.0.0.1") is None
    assert policy.rejection_reason("http://localhost:bad", "127.0.0.1") == "origin_not_allowed"


def test_production_fails_closed_even_for_configured_origin() -> None:
    settings = make_settings("production", "https://product.example")
    with TestClient(create_app(settings=settings)) as client:
        assert client.get("/health/live").status_code == 200
        try:
            with client.websocket_connect(
                "/live-ais/ws", headers={"origin": "https://product.example"}
            ):
                raise AssertionError("production WebSocket must fail closed")
        except WebSocketDisconnect as error:
            assert error.code == 1008


def test_lifespan_starts_exactly_one_configured_worker_and_cleans_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeWorker:
        instances = 0
        stopped = 0

        def __init__(self, **_: object) -> None:
            FakeWorker.instances += 1

        async def run(self) -> None:
            try:
                await asyncio.Event().wait()
            finally:
                FakeWorker.stopped += 1

    monkeypatch.setattr(main_module, "PelyrWorker", FakeWorker)
    settings = Settings.model_validate(
        {
            "environment": "test",
            "live_ais_origins": "http://testserver",
            "PELYR_API_KEY": "TEST DATA server-only key",
        }
    )
    application = create_app(settings=settings)

    with TestClient(application) as client:
        assert client.get("/health/live").status_code == 200
        assert FakeWorker.instances == 1
        assert application.state.live_ais_worker_task is not None

    assert FakeWorker.stopped == 1
    assert application.state.live_ais_gateway.client_count == 0
    assert application.state.live_ais_gateway.latest_count == 0


def test_websocket_blocked_send_preserves_recovery_sequence() -> None:
    async def scenario() -> None:
        # TEST DATA: an ASGI send gate simulates a slow connection without network calls.
        gateway = LiveAisGateway(
            worker_configured=False,
            config=LiveAisGatewayConfig(client_queue_capacity=2),
        )
        client = gateway.register_client()
        assert client is not None
        send_entered = asyncio.Event()
        release_send = asyncio.Event()
        recovery_sent = asyncio.Event()
        disconnect = asyncio.Event()
        connected = False
        sent: list[LiveAisServerEvent] = []
        adapter: TypeAdapter[LiveAisServerEvent] = TypeAdapter(LiveAisServerEvent)

        async def receive() -> MutableMapping[str, object]:
            nonlocal connected
            if not connected:
                connected = True
                return {"type": "websocket.connect"}
            await disconnect.wait()
            return {"type": "websocket.disconnect", "code": 1000}

        async def send(message: MutableMapping[str, object]) -> None:
            if message["type"] != "websocket.send":
                return
            payload = message["text"]
            assert isinstance(payload, str)
            event = adapter.validate_json(payload)
            if event.sequence == 1:
                send_entered.set()
                await release_send.wait()
            sent.append(event)
            if event.event == "vessel.snapshot" and event.sequence > 0:
                recovery_sent.set()

        websocket = WebSocket(
            {"type": "websocket", "path": "/live-ais/ws", "headers": []},
            receive=receive,
            send=send,
        )
        await websocket.accept()
        task = asyncio.create_task(_serve_client(websocket, client))
        try:
            async with asyncio.timeout(2):
                await send_entered.wait()
                for _ in range(3):
                    gateway.status_sink(
                        PelyrWorkerStatusEvent(
                            event="worker.status",
                            occurred_at=datetime(2026, 10, 13, tzinfo=UTC),
                            connection_state="DISCONNECTED",
                            freshness="OFFLINE",
                            availability="DATA UNAVAILABLE",
                            reason="shutdown",
                            reconnect_attempt=0,
                            stream_epoch=None,
                            replay_available=False,
                            metrics=PelyrWorkerMetrics(),
                        )
                    )
                assert client.queue_depth == 2
                release_send.set()
                await recovery_sent.wait()
                disconnect.set()
                await task
            assert [event.event for event in sent] == [
                "vessel.snapshot",
                "stream.status",
                "stream.gap",
                "vessel.snapshot",
            ]
            assert [event.sequence for event in sent] == [0, 1, 2, 3]
            assert client.last_sent_sequence == 3
        finally:
            release_send.set()
            disconnect.set()
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            await gateway.stop()

    asyncio.run(scenario())
