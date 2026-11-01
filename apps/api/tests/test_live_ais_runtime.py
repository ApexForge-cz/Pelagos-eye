"""TEST DATA only: local runtime configuration and sanitized acceptance checks."""

import asyncio
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient
from uvicorn._types import (
    ASGIReceiveCallable,
    ASGIReceiveEvent,
    ASGISendCallable,
    ASGISendEvent,
    Scope,
)
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from oceanscope_api import main as main_module
from oceanscope_api.api.contracts.live_ais import LiveAisPosition, LiveAisProvenance
from oceanscope_api.api.routes.live_ais import LiveAisAccessPolicy
from oceanscope_api.core.settings import Settings

ROOT = Path(__file__).parents[3]
ORIGINS = "http://localhost:4173,http://localhost:5173"
SPEC = importlib.util.spec_from_file_location(
    "live_ais_runtime_smoke", ROOT / "scripts" / "smoke_live_ais_runtime.py"
)
assert SPEC is not None and SPEC.loader is not None
smoke = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = smoke
SPEC.loader.exec_module(smoke)


@pytest.fixture
def no_key_events() -> list[dict[str, object]]:
    settings = Settings.model_validate(
        {"environment": "test", "PELYR_API_KEY": None, "live_ais_origins": ORIGINS}
    )
    with (
        TestClient(main_module.create_app(settings=settings)) as client,
        client.websocket_connect(
            "/live-ais/ws", headers={"origin": "http://localhost:4173"}
        ) as socket,
    ):
        return [socket.receive_json(), socket.receive_json()]


def test_no_key_smoke_validates_real_product_events(no_key_events: list[dict[str, object]]) -> None:
    check = smoke.StreamCheck("no-key")
    for event in no_key_events:
        check.accept(json.dumps(event))
    check.finish()
    assert check.events == 2
    assert check.observations == 0


@pytest.mark.parametrize("key", [None, "", "   "])
@pytest.mark.parametrize("origin", ORIGINS.split(","))
def test_local_origins_and_blank_keys_keep_api_healthy_without_worker(
    key: str | None, origin: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_worker(**_: object) -> None:
        pytest.fail("A blank key must not construct a provider worker")

    monkeypatch.setattr(main_module, "PelyrWorker", forbidden_worker)
    settings = Settings.model_validate(
        {"environment": "development", "PELYR_API_KEY": key, "live_ais_origins": ORIGINS}
    )
    application = main_module.create_app(settings=settings)
    with TestClient(application, client=("127.0.0.1", 12345)) as client:
        response = client.get("/health/ready")
        assert response.json()["service"] == "oceanscope-api"
        assert response.json()["status"] == "ready"
        assert application.state.live_ais_worker_task is None
        with client.websocket_connect(
            "/live-ais/ws", headers={"origin": origin, "x-forwarded-for": "203.0.113.10"}
        ) as socket:
            check = smoke.StreamCheck("no-key")
            check.accept(socket.receive_text())
            check.accept(socket.receive_text())
            check.finish()
    assert application.state.live_ais_gateway.client_count == 0
    assert application.state.live_ais_gateway.latest_count == 0


def test_local_topology_does_not_trust_client_forwarded_addresses() -> None:
    policy = LiveAisAccessPolicy("development", frozenset(ORIGINS.split(",")))

    async def check(peer: str, forwarded: str) -> str | None:
        result: list[str | None] = []

        async def application(
            scope: Scope, _receive: ASGIReceiveCallable, _send: ASGISendCallable
        ) -> None:
            assert scope["type"] == "websocket"
            client = cast(tuple[str, int], scope["client"])
            result.append(policy.rejection_reason("http://localhost:4173", client[0]))

        async def receive() -> ASGIReceiveEvent:
            return {"type": "websocket.disconnect", "code": 1000}

        async def send(_message: ASGISendEvent) -> None:
            pass

        middleware = ProxyHeadersMiddleware(application, trusted_hosts=[])
        await middleware(
            cast(
                Scope,
                {
                    "type": "websocket",
                    "scheme": "ws",
                    "client": (peer, 12345),
                    "headers": [(b"x-forwarded-for", forwarded.encode())],
                },
            ),
            receive,
            send,
        )
        return result[0]

    assert asyncio.run(check("127.0.0.1", "203.0.113.10")) is None
    assert asyncio.run(check("203.0.113.10", "127.0.0.1")) == "loopback_only"


@pytest.mark.parametrize(
    "url",
    [
        "ws://remote.invalid:4173/live-ais/ws",
        "ws://localhost:4173/live-ais/ws?key=TEST_DATA",
        "ws://TEST_DATA@localhost:4173/live-ais/ws",
        "ws://localhost:4173/live-ais/ws#TEST_DATA",
        "ws://localhost:4173/unrelated",
        "ws://localhost/live-ais/ws",
        "ws://localhost:invalid/live-ais/ws",
        "http://localhost:4173/live-ais/ws",
    ],
)
def test_smoke_refuses_remote_or_credential_bearing_endpoints(url: str) -> None:
    with pytest.raises(smoke.SmokeFailure):
        smoke.require_local_url(url, websocket=True)


@pytest.mark.parametrize("url", ["ws://localhost:4173/live-ais/ws", "ws://[::1]:5173/live-ais/ws"])
def test_smoke_accepts_explicit_loopback_endpoints(url: str) -> None:
    smoke.require_local_url(url, websocket=True)


def test_smoke_rejects_missing_snapshot_and_duplicate_sequences(
    no_key_events: list[dict[str, object]],
) -> None:
    with pytest.raises(smoke.SmokeFailure, match="snapshot"):
        smoke.StreamCheck("no-key").accept(json.dumps(no_key_events[1]))
    check = smoke.StreamCheck("no-key")
    check.accept(json.dumps(no_key_events[0]))
    no_key_events[1]["sequence"] = no_key_events[0]["sequence"]
    with pytest.raises(smoke.SmokeFailure, match="Sequence"):
        check.accept(json.dumps(no_key_events[1]))


def test_smoke_rejects_changed_coverage_and_false_no_key_claims(
    no_key_events: list[dict[str, object]],
) -> None:
    payload = json.loads(json.dumps(no_key_events[0]))
    payload["coverage"]["bounds"]["west"] = 22.0
    with pytest.raises(smoke.SmokeFailure, match="bounds"):
        smoke.StreamCheck("no-key").accept(json.dumps(payload))
    no_key_events[0]["availability"] = "AVAILABLE"
    with pytest.raises(smoke.SmokeFailure, match="DATA UNAVAILABLE"):
        smoke.StreamCheck("no-key").accept(json.dumps(no_key_events[0]))


def test_smoke_does_not_claim_live_acceptance_without_observations(
    no_key_events: list[dict[str, object]],
) -> None:
    check = smoke.StreamCheck("live")
    for event in no_key_events:
        check.accept(json.dumps(event))
    with pytest.raises(smoke.SmokeFailure, match="incomplete"):
        check.finish()


def test_smoke_enforces_gap_recovery_and_checks_attributed_positions(
    no_key_events: list[dict[str, object]],
) -> None:
    # TEST DATA: fictional position used only to test the acceptance checker.
    now = datetime.now(UTC)
    position = LiveAisPosition(
        observation_id="TEST DATA",
        mmsi="123456789",
        observed_at=now,
        longitude=24.5,
        latitude=60.0,
        quality_flags=("TEST DATA",),
        provenance=LiveAisProvenance(
            source_slug="test-data",
            source_url="https://example.invalid/test-data",
            attribution_text="TEST DATA",
            data_version="test-data",
            schema_version="test-data",
            provider_message_type="TEST DATA",
            ingested_at=now,
            normalized_at=now,
            source_state="LIVE",
        ),
    )
    check = smoke.StreamCheck("live")
    for event in no_key_events:
        check.accept(json.dumps(event))
    gap = {
        "event": "stream.gap",
        "stream_epoch": no_key_events[0]["stream_epoch"],
        "sequence": 2,
        "emitted_at": now.isoformat(),
        "gap_started_at": now.isoformat(),
        "gap_ended_at": None,
        "reason": "provider_disconnect",
        "detail": "TEST DATA",
    }
    check.accept(json.dumps(gap))
    position_event = {
        "event": "vessel.position",
        "stream_epoch": no_key_events[0]["stream_epoch"],
        "sequence": 3,
        "emitted_at": now.isoformat(),
        "position": position.model_dump(mode="json"),
    }
    with pytest.raises(smoke.SmokeFailure, match="fresh continuity snapshot"):
        check.accept(json.dumps(position_event))
    replacement = dict(no_key_events[0], sequence=4)
    check.accept(json.dumps(replacement))
    position_event["sequence"] = 5
    check.accept(json.dumps(position_event))
    check.finish()
    assert check.observations == 1
    position_event["sequence"] = 6
    bad_position = position.model_copy(update={"longitude": 0.0})
    position_event["position"] = bad_position.model_dump(mode="json")
    with pytest.raises(smoke.SmokeFailure, match="bounds, attribution, or freshness"):
        check.accept(json.dumps(position_event))


def test_smoke_suppresses_validation_and_network_payloads(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret_marker = "TEST DATA private input must not be printed"
    with pytest.raises(smoke.SmokeFailure) as failure:
        smoke.StreamCheck("no-key").accept(secret_marker)
    assert secret_marker not in str(failure.value)

    def broken_ready(_url: str) -> None:
        raise RuntimeError(secret_marker)

    monkeypatch.setattr(smoke, "check_ready", broken_ready)
    monkeypatch.setattr(sys, "argv", ["smoke_live_ais_runtime.py"])
    assert smoke.main() == 1
    captured = capsys.readouterr()
    assert "RuntimeError" in captured.out
    assert secret_marker not in captured.out + captured.err


@pytest.mark.parametrize(
    "body",
    [
        "<html>TEST DATA SPA fallback</html>",
        '{"status":"ready"}',
        '{"service":"oceanscope-api","status":"ok"}',
    ],
)
def test_readiness_rejects_spa_or_incorrect_health_responses(
    body: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Opener:
        def open(self, _url: str, *, timeout: int) -> StringIO:
            assert timeout > 0
            return StringIO(body)

    monkeypatch.setattr(smoke, "build_opener", lambda *_: Opener())
    with pytest.raises(smoke.SmokeFailure) as failure:
        smoke.check_ready("http://localhost:18000/health/ready")
    assert body not in str(failure.value)


def test_readiness_accepts_only_explicit_api_ready_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class Opener:
        def open(self, _url: str, *, timeout: int) -> StringIO:
            assert timeout > 0
            return StringIO('{"service":"oceanscope-api","status":"ready"}')

    monkeypatch.setattr(smoke, "build_opener", lambda *_: Opener())
    smoke.check_ready("http://localhost:18000/health/ready")


@dataclass
class ComposeConfiguration:
    command: list[str]
    env: dict[str, str]


@pytest.fixture
def compose_configuration(tmp_path: Path) -> ComposeConfiguration:
    env = dict(os.environ)
    env.update(
        {
            "DOCKER_CONFIG": str(tmp_path / "docker"),
            "OCEANSCOPE_POSTGRES_DB": "test_data",
            "OCEANSCOPE_POSTGRES_USER": "test_data",
            "OCEANSCOPE_POSTGRES_PASSWORD": "test_data",
            "OCEANSCOPE_DATABASE_URL": "postgresql+psycopg://test_data:test_data@postgres/test_data",
            "OCEANSCOPE_REDIS_URL": "redis://redis:6379/0",
            "OCEANSCOPE_CORS_ORIGINS": ORIGINS,
            "OCEANSCOPE_LIVE_AIS_ORIGINS": "http://localhost:5173",
        }
    )
    env_file = tmp_path / "test-data.env"
    env_file.write_text("# TEST DATA: no real .env or credential is loaded.\n", encoding="utf-8")
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker Compose CLI is required for configuration integration checks")
    docker_config = tmp_path / "docker"
    docker_config.mkdir()
    # Desktop may install Compose beside its CLI instead of a global plugin dir.
    # Write only this public path; never read or copy the user's credential config.
    plugins = Path(docker).resolve().parent.parent / "cli-plugins"
    if plugins.is_dir():
        (docker_config / "config.json").write_text(
            json.dumps({"cliPluginsExtraDirs": [str(plugins)]}), encoding="utf-8"
        )
    command = [
        docker,
        "compose",
        "--env-file",
        str(env_file),
        "-f",
        str(ROOT / "infra/compose.yaml"),
    ]
    version = subprocess.run(
        [docker, "compose", "version"], env=env, capture_output=True, check=False
    )
    if version.returncode:
        pytest.skip("Docker Compose plugin is required for configuration integration checks")
    return ComposeConfiguration(command, env)


@pytest.mark.integration
@pytest.mark.parametrize("key", [None, "", "   ", "TEST DATA"])
def test_compose_preserves_local_security_and_server_only_key(
    compose_configuration: ComposeConfiguration, key: str | None
) -> None:
    config = compose_configuration
    config.env.pop("PELYR_API_KEY", None)
    if key is not None:
        config.env["PELYR_API_KEY"] = key
    result = subprocess.run(
        [*config.command, "config", "--format", "json"],
        env=config.env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Compose configuration failed; output deliberately suppressed"
    services = json.loads(result.stdout)["services"]
    api, web = services["api"], services["web"]
    assert api["environment"]["PELYR_API_KEY"] == (key or "")
    assert api["environment"]["OCEANSCOPE_LIVE_AIS_ORIGINS"] == ORIGINS
    assert "--no-proxy-headers" in api["command"]
    assert {str(port["published"]) for port in api["ports"]} == {"8000", "4173"}
    assert {str(port["published"]): port["target"] for port in api["ports"]} == {
        "8000": 8081,
        "4173": 8080,
    }
    assert all(port["host_ip"] == "127.0.0.1" for port in api["ports"])
    assert web["network_mode"] == "service:api"
    assert web["depends_on"]["api"]["restart"] is True
    assert not web.get("ports")
    assert not web.get("environment")
    assert not web["build"].get("args")


def test_nginx_preserves_websocket_headers_and_existing_http_routes() -> None:
    config = (ROOT / "infra/nginx.conf").read_text(encoding="utf-8")
    websocket = config.split("location /live-ais/ {", 1)[1].split("\n    }", 1)[0]
    for directive in (
        "proxy_pass http://127.0.0.1:8000;",
        "proxy_http_version 1.1;",
        "proxy_set_header Upgrade $http_upgrade;",
        "proxy_set_header Connection $connection_upgrade;",
        "proxy_set_header Host $http_host;",
        "proxy_set_header Origin $http_origin;",
        "proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;",
        "proxy_set_header X-Forwarded-Proto $scheme;",
        "proxy_read_timeout 60s;",
    ):
        assert directive in websocket
    assert "try_files $uri $uri/ /index.html;" in config
    assert "http://api:8000" not in config
    for location in ("/data/", "/system/", "/ports", "/earthquakes", "/ocean/"):
        assert f"location {location} {{" in config
    api_passthrough = config.split("listen 8081;", 1)[1]
    assert "proxy_pass http://127.0.0.1:8000;" in api_passthrough
    assert "proxy_http_version 1.1;" in api_passthrough
    assert "proxy_set_header Origin $http_origin;" in api_passthrough
    assert "try_files" not in api_passthrough
