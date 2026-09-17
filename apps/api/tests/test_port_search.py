from datetime import UTC, datetime
from uuid import UUID

import pytest

from oceanscope_api.api.routes.ports import search_ports
from oceanscope_api.core.errors import SourceDataUnavailableError
from oceanscope_api.main import app
from oceanscope_api.ports.contracts import (
    PortSearchQuery,
    PortSearchRecord,
    PortSearchResult,
)
from oceanscope_api.ports.service import PortSearchService
from oceanscope_api.status.contracts import SourceAvailabilitySnapshot

NOW = datetime(2026, 9, 17, 9, 0, tzinfo=UTC)


def test_search_service_normalizes_user_filters() -> None:
    class StubRepository:
        query: PortSearchQuery | None = None

        def search(self, query: PortSearchQuery) -> PortSearchResult:
            self.query = query
            return PortSearchResult(records=(), total=0)

    repository = StubRepository()
    service = PortSearchService(repository)

    service.search(
        PortSearchQuery(
            text="  test data port  ",
            country_code=" ts ",
            has_coordinates=True,
            limit=25,
            offset=50,
        )
    )

    assert repository.query == PortSearchQuery(
        text="test data port",
        country_code="TS",
        has_coordinates=True,
        limit=25,
        offset=50,
    )


def test_search_service_rejects_expired_source_data() -> None:
    class EmptyRepository:
        def search(self, query: PortSearchQuery) -> PortSearchResult:
            return PortSearchResult(records=(), total=0)

    class OfflineAvailability:
        def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
            assert slug == "unece-unlocode"
            return SourceAvailabilitySnapshot(
                state="OFFLINE", has_usable_data=False, cache_age_seconds=None
            )

    with pytest.raises(SourceDataUnavailableError, match="UN/LOCODE"):
        PortSearchService(EmptyRepository(), OfflineAvailability()).search(
            PortSearchQuery(limit=25, offset=0)
        )


def test_search_service_rejects_missing_source_data() -> None:
    class EmptyRepository:
        def search(self, query: PortSearchQuery) -> PortSearchResult:
            return PortSearchResult(records=(), total=0)

    class MissingAvailability:
        def get_source_availability(self, slug: str) -> SourceAvailabilitySnapshot | None:
            assert slug == "unece-unlocode"
            return None

    with pytest.raises(SourceDataUnavailableError, match="UN/LOCODE"):
        PortSearchService(EmptyRepository(), MissingAvailability()).search(
            PortSearchQuery(limit=25, offset=0)
        )


class StubPortSearchService(PortSearchService):
    def __init__(self) -> None:
        pass

    def search(self, query: PortSearchQuery) -> PortSearchResult:
        assert query == PortSearchQuery(
            text="TEST DATA",
            country_code="ts",
            has_coordinates=True,
            limit=10,
            offset=20,
        )
        return PortSearchResult(
            total=1,
            records=(
                PortSearchRecord(
                    id=UUID("00000000-0000-0000-0000-000000000001"),
                    source_record_id="TST",
                    record_type="unlocode",
                    name="TEST DATA Port",
                    country_code="TS",
                    un_locode="TSTST",
                    longitude=45.5,
                    latitude=12.5667,
                    coordinate_accuracy="published_degrees_minutes",
                    function_code="1-------",
                    source_status="AA",
                    source_updated_value="2609",
                    quality_flags=("coverage_unknown",),
                    normalized_at=NOW,
                    source_slug="test-source",
                    source_display_name="TEST DATA Source",
                    source_url="https://example.test/source.csv",
                    attribution_text="TEST DATA attribution",
                    data_version="TEST-DATA-1",
                    schema_version="test-schema-v1",
                    published_at=NOW,
                    retrieved_at=NOW,
                    ingested_at=NOW,
                    source_state="LIVE",
                    cache_age_seconds=None,
                ),
            ),
        )


def test_port_search_endpoint_exposes_bounded_records_and_provenance() -> None:
    response = search_ports(
        StubPortSearchService(),
        q="TEST DATA",
        country_code="ts",
        has_coordinates=True,
        limit=10,
        offset=20,
    )

    payload = response.model_dump(mode="json")
    assert payload["total"] == 1
    assert payload["limit"] == 10
    assert payload["offset"] == 20
    record = payload["records"][0]
    assert record["un_locode"] == "TSTST"
    assert record["longitude"] == 45.5
    assert record["quality_flags"] == ["coverage_unknown"]
    assert record["provenance"]["source_slug"] == "test-source"
    assert record["provenance"]["source_state"] == "LIVE"
    assert "raw_record" not in record
    assert "artifact_reference" not in record["provenance"]


def test_port_search_endpoint_rejects_unbounded_page_size() -> None:
    operation = app.openapi()["paths"]["/ports"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}

    assert parameters["limit"]["schema"]["maximum"] == 100
    assert parameters["offset"]["schema"]["maximum"] == 100_000
