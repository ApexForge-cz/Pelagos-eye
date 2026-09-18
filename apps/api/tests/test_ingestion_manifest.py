from datetime import UTC, datetime
from uuid import UUID

import pytest

from oceanscope_api.provenance.manifest import (
    IngestionManifest,
    IngestionManifestService,
    ManifestIngestionRun,
    ManifestNotFoundError,
    ManifestSource,
    ManifestSourceVersion,
)

RUN_ID = UUID("00000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 9, 18, tzinfo=UTC)


def manifest() -> IngestionManifest:
    return IngestionManifest(
        manifest_schema_version="oceanscope-ingestion-manifest-v1",
        source=ManifestSource(
            slug="test-source",
            display_name="TEST DATA Source",
            official_url="https://example.test/source",
            terms_url="https://example.test/terms",
            attribution_text="TEST DATA attribution",
            license_identifier="TEST-ONLY",
            redistribution_status="allowed",
            terms_reviewed_at=NOW,
        ),
        source_version=ManifestSourceVersion(
            data_version="TEST-DATA-1",
            schema_version="test-schema-v1",
            source_url="https://example.test/source/data.json",
            publication_status="production",
            published_at=NOW,
            retrieved_at=NOW,
            checksum_algorithm="sha256",
            checksum="0" * 64,
            artifact_reference="raw/test-source/TEST-DATA.json",
        ),
        ingestion_run=ManifestIngestionRun(
            id=RUN_ID,
            idempotency_key="TEST-DATA-key",
            status="succeeded",
            source_state="LIVE",
            cache_age_seconds=None,
            started_at=NOW,
            finished_at=NOW,
            records_received=1,
            records_accepted=1,
            records_rejected=0,
            parameters={"scope": "TEST DATA"},
            code_revision="TEST-DATA-revision",
            failure_reason=None,
        ),
        quality_issues=(),
    )


class StubRepository:
    def __init__(self, value: IngestionManifest | None) -> None:
        self._value = value

    def get_manifest(self, run_id: UUID) -> IngestionManifest | None:
        assert run_id == RUN_ID
        return self._value


def test_manifest_service_returns_complete_reproducibility_contract() -> None:
    result = IngestionManifestService(StubRepository(manifest())).export(RUN_ID)

    assert result.source.slug == "test-source"
    assert result.source_version is not None
    assert result.source_version.checksum == "0" * 64
    assert result.ingestion_run.parameters == {"scope": "TEST DATA"}
    assert result.ingestion_run.code_revision == "TEST-DATA-revision"


def test_manifest_service_rejects_unknown_run() -> None:
    with pytest.raises(ManifestNotFoundError, match=str(RUN_ID)):
        IngestionManifestService(StubRepository(None)).export(RUN_ID)
