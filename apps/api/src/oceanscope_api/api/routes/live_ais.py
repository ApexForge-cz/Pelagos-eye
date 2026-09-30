"""Same-origin, development-only product WebSocket for bounded Live AIS events."""

from __future__ import annotations

import asyncio
from collections.abc import MutableMapping
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from oceanscope_api.api.contracts.live_ais import LiveAisServerEvent
from oceanscope_api.core.settings import Settings
from oceanscope_api.live_ais.gateway import LiveAisClient, LiveAisGateway

router = APIRouter(prefix="/live-ais", tags=["live-ais"])


@dataclass(frozen=True, slots=True)
class LiveAisAccessPolicy:
    environment: Literal["development", "test", "production"]
    allowed_origins: frozenset[str]

    @classmethod
    def from_settings(cls, settings: Settings) -> LiveAisAccessPolicy:
        return cls(settings.environment, frozenset(settings.live_ais_origin_list))

    def rejection_reason(self, origin: str | None, client_host: str | None) -> str | None:
        if self.environment == "production":
            return "production_session_required"
        if origin is None or origin.strip().lower() == "null":
            return "origin_required"
        if origin not in self.allowed_origins:
            return "origin_not_allowed"
        try:
            parsed = urlsplit(origin)
            _ = parsed.port
        except ValueError:
            return "origin_not_allowed"
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return "origin_not_allowed"
        if self.environment == "development":
            loopback_hosts = {"localhost", "127.0.0.1", "::1"}
            if parsed.hostname not in loopback_hosts or client_host not in loopback_hosts:
                return "loopback_only"
        return None


@router.websocket("/ws")
async def live_ais_websocket(websocket: WebSocket) -> None:
    settings = _settings(websocket)
    policy = LiveAisAccessPolicy.from_settings(settings)
    client_host = websocket.client.host if websocket.client is not None else None
    rejection = policy.rejection_reason(websocket.headers.get("origin"), client_host)
    if rejection is not None:
        await websocket.close(code=1008, reason=rejection)
        return

    gateway = _gateway(websocket)
    client = gateway.register_client()
    if client is None:
        await websocket.close(code=1013, reason="client_limit")
        return

    try:
        await websocket.accept()
        await _serve_client(websocket, client)
    finally:
        gateway.unregister_client(client)


async def _serve_client(websocket: WebSocket, client: LiveAisClient) -> None:
    event_task: asyncio.Task[LiveAisServerEvent | None] | None = asyncio.create_task(
        client.next_event()
    )
    receive_task: asyncio.Task[MutableMapping[str, object]] | None = asyncio.create_task(
        websocket.receive()
    )
    try:
        while event_task is not None and receive_task is not None:
            done, _ = await asyncio.wait(
                {event_task, receive_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if receive_task in done:
                message = receive_task.result()
                if not isinstance(message, dict) or message.get("type") == "websocket.disconnect":
                    return
                await websocket.close(code=1008, reason="client_messages_not_supported")
                return
            event = event_task.result()
            if event is None:
                await websocket.close(code=1013, reason="slow_client")
                return
            await websocket.send_text(event.model_dump_json())
            client.mark_sent(event)
            event_task = asyncio.create_task(client.next_event())
    except WebSocketDisconnect:
        return
    finally:
        for task in (event_task, receive_task):
            if task is not None and not task.done():
                task.cancel()
        with suppress(asyncio.CancelledError):
            if event_task is not None:
                await event_task
        with suppress(asyncio.CancelledError):
            if receive_task is not None:
                await receive_task


def _gateway(websocket: WebSocket) -> LiveAisGateway:
    gateway = getattr(websocket.app.state, "live_ais_gateway", None)
    if not isinstance(gateway, LiveAisGateway):
        raise RuntimeError("Live AIS gateway is unavailable")
    return gateway


def _settings(websocket: WebSocket) -> Settings:
    settings = getattr(websocket.app.state, "settings", None)
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are unavailable")
    return settings
