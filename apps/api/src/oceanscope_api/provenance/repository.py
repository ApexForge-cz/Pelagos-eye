from __future__ import annotations

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from oceanscope_api.provenance.models import DataSource, IngestionRun, QualityIssue, SourceVersion


class ProvenanceRepository(Protocol):
    def get_source(self, source_id: UUID) -> DataSource | None: ...

    def get_source_by_slug(self, slug: str) -> DataSource | None: ...

    def add_source(self, source: DataSource) -> None: ...

    def get_version(self, source_id: UUID, data_version: str) -> SourceVersion | None: ...

    def get_version_by_id(self, version_id: UUID) -> SourceVersion | None: ...

    def add_version(self, version: SourceVersion) -> None: ...

    def get_run(self, run_id: UUID) -> IngestionRun | None: ...

    def get_run_by_idempotency_key(
        self, source_id: UUID, idempotency_key: str
    ) -> IngestionRun | None: ...

    def add_run(self, run: IngestionRun) -> None: ...

    def add_quality_issue(self, issue: QualityIssue) -> None: ...

    def flush(self) -> None: ...


class SqlAlchemyProvenanceRepository:
    """Persist provenance entities without owning the caller's transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_source(self, source_id: UUID) -> DataSource | None:
        return self._session.get(DataSource, source_id)

    def get_source_by_slug(self, slug: str) -> DataSource | None:
        statement = select(DataSource).where(DataSource.slug == slug)
        return self._session.scalar(statement)

    def add_source(self, source: DataSource) -> None:
        self._session.add(source)

    def get_version(self, source_id: UUID, data_version: str) -> SourceVersion | None:
        statement = select(SourceVersion).where(
            SourceVersion.data_source_id == source_id,
            SourceVersion.data_version == data_version,
        )
        return self._session.scalar(statement)

    def get_version_by_id(self, version_id: UUID) -> SourceVersion | None:
        return self._session.get(SourceVersion, version_id)

    def add_version(self, version: SourceVersion) -> None:
        self._session.add(version)

    def get_run(self, run_id: UUID) -> IngestionRun | None:
        return self._session.get(IngestionRun, run_id)

    def get_run_by_idempotency_key(
        self, source_id: UUID, idempotency_key: str
    ) -> IngestionRun | None:
        statement = select(IngestionRun).where(
            IngestionRun.data_source_id == source_id,
            IngestionRun.idempotency_key == idempotency_key,
        )
        return self._session.scalar(statement)

    def add_run(self, run: IngestionRun) -> None:
        self._session.add(run)

    def add_quality_issue(self, issue: QualityIssue) -> None:
        self._session.add(issue)

    def flush(self) -> None:
        self._session.flush()
