"""Bounded local-only AIS acceptance; never print or retain received payloads.

Run with the API environment's Python. The server owns its optional credential;
this tool accepts no credential and creates no provider connection or fixture data.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, build_opener
from uuid import UUID

from pydantic import ValidationError
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
from websockets.typing import Origin

from oceanscope_api.api.contracts.live_ais import (
    LiveAisGapEvent,
    LiveAisPosition,
    LiveAisPositionEvent,
    LiveAisSnapshotEvent,
    LiveAisStatusEvent,
    live_ais_server_event_adapter,
)

ORIGINS = ("http://localhost:4173", "http://localhost:5173")
BOUNDS = {"west": 23.5, "south": 59.5, "east": 26.5, "north": 60.5}


class SmokeFailure(Exception):
    """A fixed, payload-free acceptance failure message."""


def require_local_url(url: str, *, websocket: bool) -> None:
    try:
        parsed = urlsplit(url)
        port = parsed.port
    except ValueError:
        raise SmokeFailure("Invalid local endpoint.") from None
    schemes = {"ws", "wss"} if websocket else {"http", "https"}
    path = "/live-ais/ws" if websocket else "/health/ready"
    if (
        parsed.scheme not in schemes
        or parsed.hostname not in {"localhost", "127.0.0.1", "::1"}
        or port is None
        or parsed.path != path
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise SmokeFailure(
            "Only explicit local endpoints without credentials or queries are allowed."
        )


def check_ready(url: str) -> None:
    require_local_url(url, websocket=False)
    try:
        # Ignore ambient HTTP proxies; the check must reach the local API itself.
        with build_opener(ProxyHandler({})).open(url, timeout=5) as response:
            payload = json.load(response)
        if (
            not isinstance(payload, dict)
            or payload.get("service") != "oceanscope-api"
            or payload.get("status") != "ready"
        ):
            raise SmokeFailure("API readiness did not return the expected JSON health response.")
    except (ValueError, OSError):
        raise SmokeFailure(
            "API readiness request failed; HTML or proxy health is not API health."
        ) from None


@dataclass(slots=True)
class StreamCheck:
    mode: Literal["no-key", "live"]
    events: int = 0
    observations: int = 0
    epoch: UUID | None = None
    sequence: int = -1
    needs_snapshot: bool = True
    saw_status: bool = False

    def accept(self, payload: str | bytes) -> None:
        if not isinstance(payload, str):
            raise SmokeFailure("Product events must be text frames.")
        try:
            event = live_ais_server_event_adapter.validate_json(payload)
        except ValidationError:
            # Pydantic errors may contain the input: never expose their text.
            raise SmokeFailure("Product event failed the frozen v1 contract.") from None
        if event.stream_epoch != self.epoch:
            if not isinstance(event, LiveAisSnapshotEvent):
                raise SmokeFailure("Each connection or new epoch must begin with a snapshot.")
            self.epoch = event.stream_epoch
            self.sequence = -1
            self.needs_snapshot = True
        if event.sequence <= self.sequence:
            raise SmokeFailure("Sequence must increase strictly within an epoch.")
        self.sequence = event.sequence
        if self.mode == "no-key" and self.events == 1 and not isinstance(event, LiveAisStatusEvent):
            raise SmokeFailure("Initial snapshot must be followed by product status.")
        if isinstance(event, (LiveAisSnapshotEvent, LiveAisStatusEvent)):
            bounds = event.coverage.bounds
            if bounds is None or bounds.model_dump() != BOUNDS:
                raise SmokeFailure("Coverage must retain the fixed Gulf of Finland bounds.")
            if self.mode == "no-key" and (
                event.availability != "DATA UNAVAILABLE" or event.source_state != "OFFLINE"
            ):
                raise SmokeFailure("No-key mode must report DATA UNAVAILABLE and OFFLINE.")
        if isinstance(event, LiveAisSnapshotEvent):
            self.needs_snapshot = False
            for position in event.positions:
                self._observation(position)
        elif isinstance(event, LiveAisStatusEvent):
            self.saw_status = True
            if self.mode == "no-key" and (
                event.connection_state != "DISCONNECTED"
                or event.detail != "Server-side Pelyr key is not configured."
            ):
                raise SmokeFailure("No-key check requires an actually unconfigured worker.")
        elif isinstance(event, LiveAisGapEvent):
            self.needs_snapshot = True
        elif isinstance(event, LiveAisPositionEvent):
            if self.needs_snapshot:
                raise SmokeFailure("Position received without a fresh continuity snapshot.")
            self._observation(event.position)
        self.events += 1

    def _observation(self, position: LiveAisPosition) -> None:
        if self.mode == "no-key":
            raise SmokeFailure("No-key mode must not publish observations.")
        age = (datetime.now(UTC) - position.observed_at).total_seconds()
        if (
            not BOUNDS["west"] <= position.longitude <= BOUNDS["east"]
            or not BOUNDS["south"] <= position.latitude <= BOUNDS["north"]
            or not position.provenance.attribution_text.strip()
            or position.provenance.source_state != "LIVE"
            or not -30 <= age <= 300
        ):
            raise SmokeFailure("Observation failed bounds, attribution, or freshness checks.")
        self.observations += 1

    def finish(self) -> None:
        if self.events < 2 or not self.saw_status or self.needs_snapshot:
            raise SmokeFailure("Snapshot/status or continuity recovery was not completed.")
        if self.mode == "live" and self.observations == 0:
            raise SmokeFailure(
                "No current attributed observations received; live evidence is incomplete."
            )


async def check_rejected_origins(url: str) -> None:
    require_local_url(url, websocket=True)
    for origin in (None, "null", "https://unapproved.invalid"):
        try:
            async with connect(
                url,
                origin=Origin(origin) if origin is not None else None,
                proxy=None,
                open_timeout=5,
                close_timeout=2,
            ):
                raise SmokeFailure("An unapproved Origin was accepted.")
        except InvalidStatus as error:
            if error.response.status_code != 403:
                raise SmokeFailure("Origin rejection did not return the expected denial.") from None


async def check_stream(
    url: str, origin: str, mode: Literal["no-key", "live"], seconds: float
) -> StreamCheck:
    require_local_url(url, websocket=True)
    if origin not in ORIGINS or not 0 < seconds <= 300:
        raise SmokeFailure("Use an approved local Origin and a window between 0 and 300 seconds.")
    check = StreamCheck(mode)
    async with connect(
        url,
        origin=Origin(origin),
        proxy=None,
        open_timeout=5,
        close_timeout=2,
        max_size=8 * 1024 * 1024,
    ) as socket:
        deadline = asyncio.get_running_loop().time() + seconds
        while (remaining := deadline - asyncio.get_running_loop().time()) > 0:
            try:
                payload = await asyncio.wait_for(socket.recv(), timeout=remaining)
            except TimeoutError:
                break
            check.accept(payload)
        check.finish()
    return check


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="ws://localhost:4173/live-ais/ws")
    parser.add_argument("--origin", choices=ORIGINS, default=ORIGINS[0])
    parser.add_argument("--ready-url", default="http://localhost:8000/health/ready")
    parser.add_argument("--mode", choices=("no-key", "live"), default="no-key")
    parser.add_argument("--seconds", type=float, default=5)
    args = parser.parse_args()

    async def run() -> StreamCheck:
        await check_rejected_origins(args.url)
        return await check_stream(args.url, args.origin, args.mode, args.seconds)

    try:
        check_ready(args.ready_url)
        result = asyncio.run(run())
    except Exception as error:
        # Network exception text can include handshake bodies or endpoint details.
        message = str(error) if isinstance(error, SmokeFailure) else type(error).__name__
        print(f"FAIL: {message}")
        return 1
    print(
        "PASS: readiness, Origin denial, snapshot/status, sequence and bounds; "
        f"events={result.events}"
    )
    print(
        f"PASS: mode={args.mode}; attributed observations={result.observations}; clean client close"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
