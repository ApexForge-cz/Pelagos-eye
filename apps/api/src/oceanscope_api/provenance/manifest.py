from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oceanscope_api.provenance.models import DataSource, IngestionRun, QualityIssue, SourceVersion

MANIFEST_SCHEMA_VERSION = "oceanscope-ingestion-manifest-v1"


class ManifestNotFoundError(LookupError):
    """Raised when an ingestion run cannot be exported."""


@dataclass(frozen=True)
class ManifestSource:
    slug: str
    display_name: str
    official_url: str
    terms_url: str | None
    attribution_text: str
    license_identifier: str | None
    redistribution_status: str
    terms_reviewed_at: datetime | None


@dataclass(frozen=True)
class ManifestSourceVersion:
    data_version: str
    schema_version: str
    source_url: str
    publication_status: str
    published_at: datetime | None
    retrieved_at: datetime
    checksum_algorithm: str | None
    checksum: str | None
    artifact_reference: str | None


@dataclass(frozen=True)
class ManifestIngestionRun:
    id: UUID
    idempotency_key: str
    status: str
    source_state: str
    cache_age_seconds: int | None
    started_at: datetime
    finished_at: datetime | None
    records_received: int
    records_accepted: int
    records_rejected: int
    parameters: dict[str, Any]
    code_revision: str
    failure_reason: str | None


@dataclass(frozen=True)
class ManifestQualityIssue:
    code: str
    severity: str
    record_count: int
    message: str
    sample_reference: str | None
    details: dict[str, Any] | None


@dataclass(frozen=True)
class IngestionManifest:
    manifest_schema_version: str
    source: ManifestSource
    source_version: ManifestSourceVersion | None
    ingestion_run: ManifestIngestionRun
    quality_issues: tuple[ManifestQualityIssue, ...]


class IngestionManifestRepository(Protocol):
    def get_manifest(self, run_id: UUID) -> IngestionManifest | None: ...


class SqlAlchemyIngestionManifestRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_manifest(self, run_id: UUID) -> IngestionManifest | None:
        row = self._session.execute(
            select(IngestionRun, DataSource, SourceVersion)
            .join(DataSource, DataSource.id == IngestionRun.data_source_id)
            .outerjoin(SourceVersion, SourceVersion.id == IngestionRun.source_version_id)
            .where(IngestionRun.id == run_id)
        ).one_or_none()
        if row is None:
            return None
        run, source, version = row
        issues = self._session.scalars(
            select(QualityIssue)
            .where(QualityIssue.ingestion_run_id == run.id)
            .order_by(QualityIssue.code)
        )
        return IngestionManifest(
            manifest_schema_version=MANIFEST_SCHEMA_VERSION,
            source=ManifestSource(
                slug=source.slug,
                display_name=source.display_name,
                official_url=source.official_url,
                terms_url=source.terms_url,
                attribution_text=source.attribution_text,
                license_identifier=source.license_identifier,
                redistribution_status=source.redistribution_status,
                terms_reviewed_at=source.terms_reviewed_at,
            ),
            source_version=(
                ManifestSourceVersion(
                    data_version=version.data_version,
                    schema_version=version.schema_version,
                    source_url=version.source_url,
                    publication_status=version.publication_status,
                    published_at=version.published_at,
                    retrieved_at=version.retrieved_at,
                    checksum_algorithm=version.checksum_algorithm,
                    checksum=version.checksum,
                    artifact_reference=version.artifact_reference,
                )
                if version is not None
                else None
            ),
            ingestion_run=ManifestIngestionRun(
                id=run.id,
                idempotency_key=run.idempotency_key,
                status=run.status,
                source_state=run.source_state,
                cache_age_seconds=run.cache_age_seconds,
                started_at=run.started_at,
                finished_at=run.finished_at,
                records_received=run.records_received,
                records_accepted=run.records_accepted,
                records_rejected=run.records_rejected,
                parameters=dict(run.parameters),
                code_revision=run.code_revision,
                failure_reason=run.failure_reason,
            ),
            quality_issues=tuple(
                ManifestQualityIssue(
                    code=issue.code,
                    severity=issue.severity,
                    record_count=issue.record_count,
                    message=issue.message,
                    sample_reference=issue.sample_reference,
                    details=dict(issue.details) if issue.details is not None else None,
                )
                for issue in issues
            ),
        )


class IngestionManifestService:
    def __init__(self, repository: IngestionManifestRepository) -> None:
        self._repository = repository

    def export(self, run_id: UUID) -> IngestionManifest:
        manifest = self._repository.get_manifest(run_id)
        if manifest is None:
            raise ManifestNotFoundError(f"ingestion run {run_id} does not exist")
        return manifest
