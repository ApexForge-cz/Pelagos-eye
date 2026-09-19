import asyncio
from datetime import UTC, datetime
from uuid import UUID

from httpx import ASGITransport, AsyncClient, Response

from oceanscope_api.api.routes.data import get_source_status_service
from oceanscope_api.api.routes.system import get_system_status_service
from oceanscope_api.core.errors import DatabaseUnavailableError
from oceanscope_api.main import app
from oceanscope_api.status.contracts import (
    FreshnessSnapshot,
    IngestionRunSnapshot,
    SourceStatus,
    SourceVersionSnapshot,
)
from oceanscope_api.status.service import SystemStatusService

NOW = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)


async def request(path: str) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


class StubSourceStatusService:
    def list_sources(self) -> list[SourceStatus]:
        version_id = UUID("00000000-0000-0000-0000-000000000001")
        run = IngestionRunSnapshot(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            source_version_id=version_id,
            status="succeeded",
            source_state="LIVE",
            cache_age_seconds=None,
            started_at=NOW,
            finished_at=NOW,
            records_received=1,
            records_accepted=1,
            records_rejected=0,
        )
        version = SourceVersionSnapshot(
            id=version_id,
            data_version="TEST-DATA-1",
            schema_version="test-schema-v1",
            source_url="https://example.test/data.csv",
            published_at=None,
            retrieved_at=NOW,
        )
        return [
            SourceStatus(
                slug="test-source",
                display_name="TEST DATA Source",
                official_url="https://example.test/source",
                terms_url=None,
                attribution_text="TEST DATA attribution",
                license_identifier="TEST-ONLY",
                redistribution_status="allowed",
                state="LIVE",
                availability="AVAILABLE",
                has_usable_data=True,
                cache_age_seconds=None,
                freshness=FreshnessSnapshot(
                    age_seconds=0,
                    live_ttl_seconds=300,
                    delayed_ttl_seconds=900,
                    cache_ttl_seconds=3600,
                ),
                latest_run=run,
                latest_usable_run=run,
                latest_version=version,
                quality_issues=(),
            )
        ]


def test_data_sources_endpoint_exposes_typed_provenance() -> None:
    app.dependency_overrides[get_source_status_service] = StubSourceStatusService
    try:
        response = asyncio.run(request("/data/sources"))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    source = response.json()["sources"][0]
    assert source["slug"] == "test-source"
    assert source["state"] == "LIVE"
    assert source["latest_version"]["data_version"] == "TEST-DATA-1"
    assert source["latest_run"]["id"] == "00000000-0000-0000-0000-000000000002"
    assert source["freshness"]["live_ttl_seconds"] == 300
    assert source["cache_age_seconds"] is None


def test_data_sources_endpoint_returns_problem_when_database_is_unavailable() -> None:
    def unavailable() -> StubSourceStatusService:
        raise DatabaseUnavailableError("TEST DATA database unavailable")

    app.dependency_overrides[get_source_status_service] = unavailable
    try:
        response = asyncio.run(request("/data/sources"))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["detail"] == "The requested data is currently unavailable."
    assert "TEST DATA" not in response.text


def test_system_status_endpoint_reports_degraded_database() -> None:
    app.dependency_overrides[get_system_status_service] = lambda: SystemStatusService(
        lambda: False,
        lambda: False,
        lambda: [],
        now=lambda: NOW,
    )
    try:
        response = asyncio.run(request("/system/status"))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["overall_state"] == "DEGRADED"
    assert response.json()["database"] == {
        "state": "OFFLINE",
        "detail": "DATA UNAVAILABLE",
    }
    assert response.json()["redis"] == {
        "state": "OFFLINE",
        "detail": "DATA UNAVAILABLE",
    }
    assert response.json()["providers"] == []


def test_system_status_endpoint_exposes_provider_freshness_and_latest_run() -> None:
    source_service = StubSourceStatusService()
    app.dependency_overrides[get_system_status_service] = lambda: SystemStatusService(
        lambda: True,
        lambda: True,
        source_service.list_sources,
        now=lambda: NOW,
    )
    try:
        response = asyncio.run(request("/system/status"))
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["overall_state"] == "READY"
    assert body["redis"]["state"] == "LIVE"
    provider = body["providers"][0]
    assert provider["slug"] == "test-source"
    assert provider["state"] == "LIVE"
    assert provider["source_retrieved_at"] == NOW.isoformat().replace("+00:00", "Z")
    assert provider["latest_run"]["records_received"] == 1
    assert provider["latest_run"]["records_accepted"] == 1
