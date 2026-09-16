import logging
import time
from typing import Any
from uuid import uuid4

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def configure_logging(level: str, environment: str) -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    renderer: Any
    if environment == "development":
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    logging.basicConfig(format="%(message)s", level=level, force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


class CorrelationIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_headers = MutableHeaders(scope=scope)
        correlation_id = request_headers.get("x-correlation-id") or str(uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id
        started = time.perf_counter()
        status_code = 500

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message).append("X-Correlation-ID", correlation_id)
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            structlog.get_logger("oceanscope.request").info(
                "request_completed",
                method=scope.get("method"),
                path=scope.get("path"),
                status_code=status_code,
                duration_ms=duration_ms,
                correlation_id=correlation_id,
            )
