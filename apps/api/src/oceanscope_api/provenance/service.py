from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

from oceanscope_api.provenance.models import (
    QUALITY_CODES,
    DataSource,
    IngestionRun,
    IngestionStatus,
    PublicationStatus,
    QualityIssue,
    QualitySeverity,
    RedistributionStatus,
    SourceState,
    SourceVersion,
)
from oceanscope_api.provenance.repository import ProvenanceRepository

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class ProvenanceError(ValueError):
    """Base class for provenance contract failures."""


class ProvenanceConflictError(ProvenanceError):
    """Raised when an idempotent key identifies incompatible content."""


class ProvenanceNotFoundError(ProvenanceError):
    """Raised when a referenced provenance entity does not exist."""


class InvalidRunTransitionError(ProvenanceError):
    """Raised when an ingestion run transition violates its state machine."""


@dataclass(frozen=True)
class RegisterSource:
    slug: str
    display_name: str
    official_url: str
    attribution_text: str
    terms_url: str | None = None
    license_identifier: str | None = None
    redistribution_status: RedistributionStatus = RedistributionStatus.UNREVIEWED
    terms_reviewed_at: datetime | None = None


@dataclass(frozen=True)
class RegisterSourceVersion:
    source_id: UUID
    data_version: str
    schema_version: str
    source_url: str
    published_at: datetime | None
    retrieved_at: datetime
    publication_status: PublicationStatus = PublicationStatus.PRODUCTION
    checksum_algorithm: str | None = None
    checksum: str | None = None
    artifact_reference: str | None = None


@dataclass(frozen=True)
class StartIngestionRun:
    source_id: UUID
    source_version_id: UUID | None
    idempotency_key: str
    source_state: SourceState
    code_revision: str
    started_at: datetime
    cache_age_seconds: int | None = None
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompleteIngestionRun:
    run_id: UUID
    status: IngestionStatus
    finished_at: datetime
    records_received: int
    records_accepted: int
    records_rejected: int
    failure_reason: str | None = None


@dataclass(frozen=True)
class RecordQualityIssue:
    run_id: UUID
    code: str
    severity: QualitySeverity
    record_count: int
    message: str
    sample_reference: str | None = None
    details: dict[str, Any] | None = None


class ProvenanceService:
    def __init__(self, repository: ProvenanceRepository) -> None:
        self._repository = repository

    def register_source(self, command: RegisterSource) -> DataSource:
        _require_slug(command.slug)
        _require_text(command.display_name, "display_name")
        _require_url(command.official_url, "official_url")
        _require_text(command.attribution_text, "attribution_text")
        if command.terms_url is not None:
            _require_url(command.terms_url, "terms_url")
        if (
            command.redistribution_status is not RedistributionStatus.UNREVIEWED
            and command.terms_reviewed_at is None
        ):
            raise ProvenanceError("reviewed redistribution status requires terms_reviewed_at")
        _require_aware(command.terms_reviewed_at, "terms_reviewed_at")

        existing = self._repository.get_source_by_slug(command.slug)
        if existing is not None:
            expected = (
                command.display_name,
                command.official_url,
                command.attribution_text,
                command.terms_url,
                command.license_identifier,
                command.redistribution_status.value,
                command.terms_reviewed_at,
            )
            actual = (
                existing.display_name,
                existing.official_url,
                existing.attribution_text,
                existing.terms_url,
                existing.license_identifier,
                existing.redistribution_status,
                existing.terms_reviewed_at,
            )
            if actual != expected:
                raise ProvenanceConflictError(f"source slug {command.slug!r} already differs")
            return existing

        source = DataSource(
            id=uuid4(),
            slug=command.slug,
            display_name=command.display_name.strip(),
            official_url=command.official_url,
            terms_url=command.terms_url,
            attribution_text=command.attribution_text.strip(),
            license_identifier=command.license_identifier,
            redistribution_status=command.redistribution_status.value,
            terms_reviewed_at=command.terms_reviewed_at,
        )
        self._repository.add_source(source)
        self._repository.flush()
        return source

    def register_version(self, command: RegisterSourceVersion) -> SourceVersion:
        if self._repository.get_source(command.source_id) is None:
            raise ProvenanceNotFoundError("data source does not exist")
        _require_text(command.data_version, "data_version")
        _require_text(command.schema_version, "schema_version")
        data_version = command.data_version.strip()
        schema_version = command.schema_version.strip()
        _require_url(command.source_url, "source_url")
        _require_aware(command.published_at, "published_at")
        _require_aware(command.retrieved_at, "retrieved_at")
        if command.published_at is not None and command.retrieved_at < command.published_at:
            raise ProvenanceError("retrieved_at cannot be earlier than published_at")
        if (command.checksum_algorithm is None) != (command.checksum is None):
            raise ProvenanceError("checksum_algorithm and checksum must be supplied together")

        existing = self._repository.get_version(command.source_id, data_version)
        if existing is not None:
            expected = (
                schema_version,
                command.source_url,
                command.published_at,
                command.retrieved_at,
                command.publication_status.value,
                command.checksum_algorithm,
                command.checksum,
                command.artifact_reference,
            )
            actual = (
                existing.schema_version,
                existing.source_url,
                existing.published_at,
                existing.retrieved_at,
                existing.publication_status,
                existing.checksum_algorithm,
                existing.checksum,
                existing.artifact_reference,
            )
            if actual != expected:
                raise ProvenanceConflictError(f"source version {data_version!r} already differs")
            return existing

        version = SourceVersion(
            id=uuid4(),
            data_source_id=command.source_id,
            data_version=data_version,
            schema_version=schema_version,
            source_url=command.source_url,
            published_at=command.published_at,
            retrieved_at=command.retrieved_at,
            publication_status=command.publication_status.value,
            checksum_algorithm=command.checksum_algorithm,
            checksum=command.checksum,
            artifact_reference=command.artifact_reference,
        )
        self._repository.add_version(version)
        self._repository.flush()
        return version

    def start_run(self, command: StartIngestionRun) -> IngestionRun:
        if self._repository.get_source(command.source_id) is None:
            raise ProvenanceNotFoundError("data source does not exist")
        _require_text(command.idempotency_key, "idempotency_key")
        _require_text(command.code_revision, "code_revision")
        idempotency_key = command.idempotency_key.strip()
        code_revision = command.code_revision.strip()
        _require_aware(command.started_at, "started_at")
        if command.source_state is SourceState.CACHED:
            if command.cache_age_seconds is None or command.cache_age_seconds < 0:
                raise ProvenanceError("CACHED source state requires nonnegative cache_age_seconds")
        elif command.cache_age_seconds is not None:
            raise ProvenanceError("cache_age_seconds is only valid for CACHED source state")

        if command.source_version_id is not None:
            version = self._repository.get_version_by_id(command.source_version_id)
            if version is None or version.data_source_id != command.source_id:
                raise ProvenanceNotFoundError("source version does not belong to data source")

        existing = self._repository.get_run_by_idempotency_key(command.source_id, idempotency_key)
        if existing is not None:
            expected = (
                command.source_version_id,
                command.source_state.value,
                command.cache_age_seconds,
                code_revision,
                command.started_at,
                command.parameters,
            )
            actual = (
                existing.source_version_id,
                existing.source_state,
                existing.cache_age_seconds,
                existing.code_revision,
                existing.started_at,
                existing.parameters,
            )
            if actual != expected:
                raise ProvenanceConflictError("idempotency key already identifies another run")
            return existing

        run = IngestionRun(
            id=uuid4(),
            data_source_id=command.source_id,
            source_version_id=command.source_version_id,
            idempotency_key=idempotency_key,
            status=IngestionStatus.RUNNING.value,
            source_state=command.source_state.value,
            cache_age_seconds=command.cache_age_seconds,
            started_at=command.started_at,
            records_received=0,
            records_accepted=0,
            records_rejected=0,
            parameters=dict(command.parameters),
            code_revision=code_revision,
        )
        self._repository.add_run(run)
        self._repository.flush()
        return run

    def complete_run(self, command: CompleteIngestionRun) -> IngestionRun:
        run = self._repository.get_run(command.run_id)
        if run is None:
            raise ProvenanceNotFoundError("ingestion run does not exist")
        if run.status != IngestionStatus.RUNNING.value:
            raise InvalidRunTransitionError("only a running ingestion can be completed")
        if command.status is IngestionStatus.RUNNING:
            raise InvalidRunTransitionError("completion status cannot remain running")
        _require_aware(command.finished_at, "finished_at")
        if command.finished_at < run.started_at:
            raise ProvenanceError("finished_at cannot be earlier than started_at")
        if min(command.records_received, command.records_accepted, command.records_rejected) < 0:
            raise ProvenanceError("record counts cannot be negative")
        if command.records_accepted + command.records_rejected > command.records_received:
            raise ProvenanceError("accepted plus rejected cannot exceed received")
        if command.status is IngestionStatus.FAILED and not command.failure_reason:
            raise ProvenanceError("failed ingestion requires failure_reason")
        if command.status is not IngestionStatus.FAILED and command.failure_reason is not None:
            raise ProvenanceError("failure_reason is only valid for failed ingestion")

        run.status = command.status.value
        run.finished_at = command.finished_at
        run.records_received = command.records_received
        run.records_accepted = command.records_accepted
        run.records_rejected = command.records_rejected
        run.failure_reason = command.failure_reason
        self._repository.flush()
        return run

    def record_quality_issue(self, command: RecordQualityIssue) -> QualityIssue:
        if self._repository.get_run(command.run_id) is None:
            raise ProvenanceNotFoundError("ingestion run does not exist")
        if command.code not in QUALITY_CODES:
            raise ProvenanceError(f"unsupported quality issue code: {command.code}")
        if command.record_count <= 0:
            raise ProvenanceError("quality issue record_count must be positive")
        _require_text(command.message, "message")

        issue = QualityIssue(
            id=uuid4(),
            ingestion_run_id=command.run_id,
            code=command.code,
            severity=command.severity.value,
            record_count=command.record_count,
            message=command.message.strip(),
            sample_reference=command.sample_reference,
            details=command.details,
        )
        self._repository.add_quality_issue(issue)
        self._repository.flush()
        return issue


def _require_slug(value: str) -> None:
    if not SLUG_PATTERN.fullmatch(value):
        raise ProvenanceError("slug must contain lowercase letters, numbers, and single hyphens")


def _require_text(value: str, field_name: str) -> None:
    if not value.strip():
        raise ProvenanceError(f"{field_name} cannot be blank")


def _require_url(value: str, field_name: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ProvenanceError(f"{field_name} must be an absolute HTTP(S) URL")


def _require_aware(value: datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ProvenanceError(f"{field_name} must be timezone-aware")
