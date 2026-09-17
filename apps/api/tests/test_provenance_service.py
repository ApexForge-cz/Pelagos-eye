from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from oceanscope_api.db.base import Base
from oceanscope_api.provenance.models import (
    DataSource,
    IngestionStatus,
    QualitySeverity,
    RedistributionStatus,
    SourceState,
)
from oceanscope_api.provenance.repository import SqlAlchemyProvenanceRepository
from oceanscope_api.provenance.service import (
    CompleteIngestionRun,
    InvalidRunTransitionError,
    ProvenanceConflictError,
    ProvenanceError,
    ProvenanceNotFoundError,
    ProvenanceService,
    RecordQualityIssue,
    RegisterSource,
    RegisterSourceVersion,
    StartIngestionRun,
)

NOW = datetime(2026, 9, 17, 1, 0, tzinfo=UTC)
LATER = NOW + timedelta(hours=1)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session
    engine.dispose()


@pytest.fixture
def service(session: Session) -> ProvenanceService:
    return ProvenanceService(SqlAlchemyProvenanceRepository(session))


def source_command() -> RegisterSource:
    return RegisterSource(
        slug="test-source",
        display_name="TEST DATA Source",
        official_url="https://example.test/source",
        terms_url="https://example.test/terms",
        attribution_text="TEST DATA attribution",
        license_identifier="TEST-ONLY",
        redistribution_status=RedistributionStatus.ALLOWED,
        terms_reviewed_at=NOW,
    )


def version_command(source_id: object) -> RegisterSourceVersion:
    from uuid import UUID

    assert isinstance(source_id, UUID)
    return RegisterSourceVersion(
        source_id=source_id,
        data_version="2026-test",
        schema_version="test-v1",
        source_url="https://example.test/source/2026-test",
        published_at=NOW,
        retrieved_at=LATER,
        checksum_algorithm="sha256",
        checksum="0" * 64,
        artifact_reference="test-only://artifact",
    )


def test_provenance_lifecycle_is_traceable_and_idempotent(
    service: ProvenanceService,
) -> None:
    source = service.register_source(source_command())
    assert service.register_source(source_command()).id == source.id

    version = service.register_version(version_command(source.id))
    assert service.register_version(version_command(source.id)).id == version.id

    start = StartIngestionRun(
        source_id=source.id,
        source_version_id=version.id,
        idempotency_key="test-run-2026-09-17",
        source_state=SourceState.LIVE,
        code_revision="test-revision",
        started_at=NOW,
        parameters={"scope": "TEST DATA"},
    )
    run = service.start_run(start)
    assert service.start_run(start).id == run.id

    issue = service.record_quality_issue(
        RecordQualityIssue(
            run_id=run.id,
            code="missing_required",
            severity=QualitySeverity.WARNING,
            record_count=2,
            message="TEST DATA rows omitted a required field",
        )
    )
    assert issue.ingestion_run_id == run.id

    completed = service.complete_run(
        CompleteIngestionRun(
            run_id=run.id,
            status=IngestionStatus.PARTIAL,
            finished_at=LATER,
            records_received=10,
            records_accepted=8,
            records_rejected=2,
        )
    )

    assert completed.status == IngestionStatus.PARTIAL.value
    assert completed.records_accepted == 8
    assert completed.records_rejected == 2


def test_normalized_version_and_run_keys_remain_idempotent(
    service: ProvenanceService,
) -> None:
    source = service.register_source(source_command())
    base_version = version_command(source.id)
    version = service.register_version(
        RegisterSourceVersion(
            source_id=base_version.source_id,
            data_version=" 2026-test ",
            schema_version=" test-v1 ",
            source_url=base_version.source_url,
            published_at=base_version.published_at,
            retrieved_at=base_version.retrieved_at,
            checksum_algorithm=base_version.checksum_algorithm,
            checksum=base_version.checksum,
            artifact_reference=base_version.artifact_reference,
        )
    )
    assert service.register_version(base_version).id == version.id

    run = service.start_run(
        StartIngestionRun(
            source_id=source.id,
            source_version_id=version.id,
            idempotency_key=" normalized-run ",
            source_state=SourceState.LIVE,
            code_revision=" test-revision ",
            started_at=NOW,
        )
    )
    normalized_run = service.start_run(
        StartIngestionRun(
            source_id=source.id,
            source_version_id=version.id,
            idempotency_key="normalized-run",
            source_state=SourceState.LIVE,
            code_revision="test-revision",
            started_at=NOW,
        )
    )
    assert normalized_run.id == run.id


def test_source_slug_is_idempotent_only_for_identical_content(
    service: ProvenanceService,
) -> None:
    service.register_source(source_command())

    with pytest.raises(ProvenanceConflictError, match="already differs"):
        service.register_source(
            RegisterSource(
                slug="test-source",
                display_name="Different TEST DATA Source",
                official_url="https://example.test/source",
                attribution_text="TEST DATA attribution",
            )
        )


@pytest.mark.parametrize("slug", ["", "Test-Source", "test--source", "test_source"])
def test_source_rejects_invalid_slugs(service: ProvenanceService, slug: str) -> None:
    command = RegisterSource(
        slug=slug,
        display_name="TEST DATA Source",
        official_url="https://example.test/source",
        attribution_text="TEST DATA attribution",
    )

    with pytest.raises(ProvenanceError, match="slug"):
        service.register_source(command)


def test_reviewed_redistribution_requires_review_time(service: ProvenanceService) -> None:
    command = RegisterSource(
        slug="test-source",
        display_name="TEST DATA Source",
        official_url="https://example.test/source",
        attribution_text="TEST DATA attribution",
        redistribution_status=RedistributionStatus.RESTRICTED,
    )

    with pytest.raises(ProvenanceError, match="terms_reviewed_at"):
        service.register_source(command)


def test_version_rejects_partial_checksum(service: ProvenanceService) -> None:
    source = service.register_source(source_command())
    command = RegisterSourceVersion(
        source_id=source.id,
        data_version="2026-test",
        schema_version="test-v1",
        source_url="https://example.test/source/2026-test",
        published_at=NOW,
        retrieved_at=LATER,
        checksum_algorithm="sha256",
    )

    with pytest.raises(ProvenanceError, match="supplied together"):
        service.register_version(command)


def test_run_rejects_version_from_another_source(service: ProvenanceService) -> None:
    first = service.register_source(source_command())
    second = service.register_source(
        RegisterSource(
            slug="second-test-source",
            display_name="Second TEST DATA Source",
            official_url="https://example.test/second",
            attribution_text="TEST DATA attribution",
        )
    )
    version = service.register_version(version_command(first.id))

    with pytest.raises(ProvenanceNotFoundError, match="does not belong"):
        service.start_run(
            StartIngestionRun(
                source_id=second.id,
                source_version_id=version.id,
                idempotency_key="mismatched-test-run",
                source_state=SourceState.LIVE,
                code_revision="test-revision",
                started_at=NOW,
            )
        )


def test_completion_rejects_impossible_counts(service: ProvenanceService) -> None:
    source = service.register_source(source_command())
    run = service.start_run(
        StartIngestionRun(
            source_id=source.id,
            source_version_id=None,
            idempotency_key="count-test",
            source_state=SourceState.OFFLINE,
            code_revision="test-revision",
            started_at=NOW,
        )
    )

    with pytest.raises(ProvenanceError, match="cannot exceed"):
        service.complete_run(
            CompleteIngestionRun(
                run_id=run.id,
                status=IngestionStatus.PARTIAL,
                finished_at=LATER,
                records_received=1,
                records_accepted=1,
                records_rejected=1,
            )
        )


def test_completed_run_cannot_transition_twice(service: ProvenanceService) -> None:
    source = service.register_source(source_command())
    run = service.start_run(
        StartIngestionRun(
            source_id=source.id,
            source_version_id=None,
            idempotency_key="transition-test",
            source_state=SourceState.CACHED,
            code_revision="test-revision",
            started_at=NOW,
            cache_age_seconds=60,
        )
    )
    completion = CompleteIngestionRun(
        run_id=run.id,
        status=IngestionStatus.SUCCEEDED,
        finished_at=LATER,
        records_received=1,
        records_accepted=1,
        records_rejected=0,
    )
    service.complete_run(completion)

    with pytest.raises(InvalidRunTransitionError, match="only a running"):
        service.complete_run(completion)


def test_cached_run_requires_cache_age(service: ProvenanceService) -> None:
    source = service.register_source(source_command())

    with pytest.raises(ProvenanceError, match="cache_age_seconds"):
        service.start_run(
            StartIngestionRun(
                source_id=source.id,
                source_version_id=None,
                idempotency_key="cached-without-age",
                source_state=SourceState.CACHED,
                code_revision="test-revision",
                started_at=NOW,
            )
        )


def test_repository_changes_can_be_rolled_back(
    session: Session, service: ProvenanceService
) -> None:
    source = service.register_source(source_command())
    session.rollback()

    assert session.scalar(select(DataSource).where(DataSource.id == source.id)) is None
