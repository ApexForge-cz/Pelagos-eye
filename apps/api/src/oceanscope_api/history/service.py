from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from oceanscope_api.history.artifacts import HistoricalAisArtifactStore
from oceanscope_api.history.contracts import (
    HistoricalAisError,
    HistoricalAisParser,
    HistoricalAisProvider,
    HistoricalAisRequest,
)
from oceanscope_api.history.repository import SqlAlchemyHistoricalAisRepository
from oceanscope_api.provenance.models import (
    IngestionRun,
    IngestionStatus,
    PublicationStatus,
    QualitySeverity,
    SourceState,
)
from oceanscope_api.provenance.repository import SqlAlchemyProvenanceRepository
from oceanscope_api.provenance.service import (
    CompleteIngestionRun,
    ProvenanceService,
    RecordQualityIssue,
    RegisterSource,
    RegisterSourceVersion,
    StartIngestionRun,
)


@dataclass(frozen=True)
class HistoricalAisImportReport:
    data_version: str
    ingestion_run_id: str
    request_key: str
    status: str
    records_received: int
    records_accepted: int
    records_rejected: int
    records_filtered: int
    records_duplicate: int
    records_capped: int
    inserted: int
    unchanged: int
    artifact_reference: str


class HistoricalAisImportService:
    def __init__(
        self,
        session: Session,
        artifact_store: HistoricalAisArtifactStore,
        *,
        code_revision: str,
    ) -> None:
        if not code_revision.strip():
            raise ValueError("code_revision cannot be blank")
        self._session = session
        self._artifact_store = artifact_store
        self._code_revision = code_revision.strip()
        self._provenance = ProvenanceService(SqlAlchemyProvenanceRepository(session))
        self._positions = SqlAlchemyHistoricalAisRepository(session)

    def import_archive(
        self,
        provider: HistoricalAisProvider,
        parser: HistoricalAisParser,
        request: HistoricalAisRequest,
    ) -> HistoricalAisImportReport:
        source = self._provenance.register_source(
            RegisterSource(
                slug=provider.source.slug,
                display_name=provider.source.display_name,
                official_url=provider.source.official_url,
                terms_url=provider.source.terms_url,
                attribution_text=provider.source.attribution_text,
                license_identifier=provider.source.license_identifier,
                redistribution_status=provider.source.redistribution_status,
                terms_reviewed_at=provider.source.terms_reviewed_at,
            )
        )
        try:
            archive = provider.fetch(request)
        except HistoricalAisError as error:
            self._record_download_failure(source.id, request, str(error))
            raise

        stored = self._artifact_store.store(archive)
        version = self._provenance.register_version(
            RegisterSourceVersion(
                source_id=source.id,
                data_version=archive.data_version,
                schema_version=archive.schema_version,
                source_url=archive.source_url,
                published_at=None,
                retrieved_at=archive.retrieved_at,
                publication_status=PublicationStatus.PRODUCTION,
                checksum_algorithm="sha256",
                checksum=archive.checksum_sha256,
                artifact_reference=stored.reference,
            )
        )
        run = self._provenance.start_run(
            StartIngestionRun(
                source_id=source.id,
                source_version_id=version.id,
                idempotency_key=(
                    f"historical-ais:{request.request_key[:16]}:{archive.data_version}:"
                    f"{parser.normalization_version}:{self._code_revision}"
                ),
                source_state=archive.source_state,
                code_revision=self._code_revision,
                started_at=datetime.now(UTC),
                cache_age_seconds=archive.cache_age_seconds,
                parameters={
                    "archive_date": request.archive_date.isoformat(),
                    "bounds": [
                        request.min_longitude,
                        request.min_latitude,
                        request.max_longitude,
                        request.max_latitude,
                    ],
                    "start_at": request.start_at.astimezone(UTC).isoformat(),
                    "end_at": request.end_at.astimezone(UTC).isoformat(),
                    "record_limit": request.record_limit,
                    "request_key": request.request_key,
                    "normalization_version": parser.normalization_version,
                    "artifact_size_bytes": stored.size_bytes,
                    "coverage": "U.S. waters and other areas documented by NOAA",
                },
            )
        )
        if run.status != IngestionStatus.RUNNING.value:
            return _report_from_run(
                run, archive.data_version, request.request_key, stored.reference
            )
        try:
            parsed = parser.parse(archive)
        except HistoricalAisError as error:
            self._fail_schema_run(run.id, str(error))
            raise
        inserted = self._positions.insert_positions(
            source_version_id=version.id,
            ingestion_run_id=run.id,
            request_key=request.request_key,
            normalization_version=parser.normalization_version,
            records=parsed.records,
        )
        for code, count in sorted(parsed.quality_counts.items()):
            self._provenance.record_quality_issue(
                RecordQualityIssue(
                    run_id=run.id,
                    code=code,
                    severity=QualitySeverity.WARNING,
                    record_count=count,
                    message=f"MarineCadastre import reported {code} AIS rows",
                )
            )
        run.parameters = {
            **run.parameters,
            "records_filtered": parsed.records_filtered,
            "records_duplicate": parsed.records_duplicate,
            "records_capped": parsed.records_capped,
            "inserted": inserted.inserted,
            "unchanged": inserted.unchanged,
        }
        status = (
            IngestionStatus.PARTIAL
            if parsed.records_rejected or parsed.quality_counts
            else IngestionStatus.SUCCEEDED
        )
        completed = self._provenance.complete_run(
            CompleteIngestionRun(
                run_id=run.id,
                status=status,
                finished_at=datetime.now(UTC),
                records_received=parsed.records_received,
                records_accepted=len(parsed.records),
                records_rejected=parsed.records_rejected,
            )
        )
        self._session.commit()
        return _report_from_run(
            completed, archive.data_version, request.request_key, stored.reference
        )

    def _record_download_failure(
        self, source_id: UUID, request: HistoricalAisRequest, reason: str
    ) -> None:
        now = datetime.now(UTC)
        run = self._provenance.start_run(
            StartIngestionRun(
                source_id=source_id,
                source_version_id=None,
                idempotency_key=f"download-failure:{request.request_key[:16]}:{now.isoformat()}",
                source_state=SourceState.OFFLINE,
                code_revision=self._code_revision,
                started_at=now,
                parameters={
                    "provider": "noaa-marinecadastre-ais",
                    "request_key": request.request_key,
                },
            )
        )
        self._provenance.complete_run(
            CompleteIngestionRun(
                run_id=run.id,
                status=IngestionStatus.FAILED,
                finished_at=datetime.now(UTC),
                records_received=0,
                records_accepted=0,
                records_rejected=0,
                failure_reason=reason,
            )
        )
        self._session.commit()

    def _fail_schema_run(self, run_id: UUID, reason: str) -> None:
        self._provenance.record_quality_issue(
            RecordQualityIssue(
                run_id=run_id,
                code="provider_revision",
                severity=QualitySeverity.ERROR,
                record_count=1,
                message="MarineCadastre archive schema could not be processed",
            )
        )
        self._provenance.complete_run(
            CompleteIngestionRun(
                run_id=run_id,
                status=IngestionStatus.FAILED,
                finished_at=datetime.now(UTC),
                records_received=0,
                records_accepted=0,
                records_rejected=0,
                failure_reason=reason,
            )
        )
        self._session.commit()


def _report_from_run(
    run: IngestionRun,
    data_version: str,
    request_key: str,
    artifact_reference: str,
) -> HistoricalAisImportReport:
    return HistoricalAisImportReport(
        data_version=data_version,
        ingestion_run_id=str(run.id),
        request_key=request_key,
        status=run.status,
        records_received=run.records_received,
        records_accepted=run.records_accepted,
        records_rejected=run.records_rejected,
        records_filtered=int(run.parameters.get("records_filtered", 0)),
        records_duplicate=int(run.parameters.get("records_duplicate", 0)),
        records_capped=int(run.parameters.get("records_capped", 0)),
        inserted=int(run.parameters.get("inserted", 0)),
        unchanged=int(run.parameters.get("unchanged", 0)),
        artifact_reference=artifact_reference,
    )
