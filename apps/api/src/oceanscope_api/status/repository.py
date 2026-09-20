from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from oceanscope_api.core.errors import DatabaseUnavailableError
from oceanscope_api.db.session import get_engine
from oceanscope_api.provenance.models import DataSource, IngestionRun, QualityIssue, SourceVersion
from oceanscope_api.status.contracts import (
    IngestionRunSnapshot,
    QualityIssueSnapshot,
    SourceHistory,
    SourceVersionSnapshot,
)


class SqlAlchemySourceStatusRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_source_histories(self) -> list[SourceHistory]:
        sources = list(self._session.scalars(select(DataSource).order_by(DataSource.slug)))
        if not sources:
            return []

        source_ids = [source.id for source in sources]
        versions = list(
            self._session.scalars(
                select(SourceVersion)
                .where(SourceVersion.data_source_id.in_(source_ids))
                .order_by(SourceVersion.retrieved_at.desc())
            )
        )
        runs = list(
            self._session.scalars(
                select(IngestionRun)
                .where(IngestionRun.data_source_id.in_(source_ids))
                .order_by(IngestionRun.started_at.desc())
            )
        )
        run_ids = [run.id for run in runs]
        issues = (
            list(
                self._session.scalars(
                    select(QualityIssue)
                    .where(QualityIssue.ingestion_run_id.in_(run_ids))
                    .order_by(QualityIssue.code)
                )
            )
            if run_ids
            else []
        )

        versions_by_source: dict[UUID, list[SourceVersionSnapshot]] = defaultdict(list)
        for version in versions:
            versions_by_source[version.data_source_id].append(
                SourceVersionSnapshot(
                    id=version.id,
                    data_version=version.data_version,
                    schema_version=version.schema_version,
                    source_url=version.source_url,
                    published_at=version.published_at,
                    retrieved_at=version.retrieved_at,
                )
            )

        runs_by_source: dict[UUID, list[IngestionRunSnapshot]] = defaultdict(list)
        for run in runs:
            runs_by_source[run.data_source_id].append(
                IngestionRunSnapshot(
                    id=run.id,
                    source_version_id=run.source_version_id,
                    status=run.status,
                    source_state=run.source_state,
                    cache_age_seconds=run.cache_age_seconds,
                    started_at=run.started_at,
                    finished_at=run.finished_at,
                    records_received=run.records_received,
                    records_accepted=run.records_accepted,
                    records_rejected=run.records_rejected,
                )
            )

        issues_by_source: dict[UUID, list[QualityIssueSnapshot]] = defaultdict(list)
        run_sources = {run.id: run.data_source_id for run in runs}
        for issue in issues:
            issues_by_source[run_sources[issue.ingestion_run_id]].append(
                QualityIssueSnapshot(
                    ingestion_run_id=issue.ingestion_run_id,
                    code=issue.code,
                    severity=issue.severity,
                    record_count=issue.record_count,
                    message=issue.message,
                )
            )

        return [
            SourceHistory(
                slug=source.slug,
                display_name=source.display_name,
                official_url=source.official_url,
                terms_url=source.terms_url,
                attribution_text=source.attribution_text,
                license_identifier=source.license_identifier,
                redistribution_status=source.redistribution_status,
                versions=tuple(versions_by_source[source.id]),
                runs=tuple(runs_by_source[source.id]),
                quality_issues=tuple(issues_by_source[source.id]),
            )
            for source in sources
        ]


class ManagedSqlAlchemySourceStatusRepository:
    """Open a short-lived session so system health can report database outages."""

    def list_source_histories(self) -> list[SourceHistory]:
        try:
            with Session(get_engine()) as session:
                return SqlAlchemySourceStatusRepository(session).list_source_histories()
        except DatabaseUnavailableError:
            raise
        except SQLAlchemyError as error:
            raise DatabaseUnavailableError("database status query failed") from error
