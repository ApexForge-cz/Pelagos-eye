from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from oceanscope_api.core.errors import InvalidQueryError, SourceDataUnavailableError
from oceanscope_api.ocean.artifacts import MarineForecastArtifactStore
from oceanscope_api.ocean.contracts import (
    MarineDataError,
    MarineForecastParser,
    MarineForecastProvider,
    MarineForecastQuery,
    MarineForecastQueryRepository,
    MarineForecastQueryResult,
    MarineForecastRequest,
)
from oceanscope_api.ocean.repository import SqlAlchemyMarineForecastRepository
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
from oceanscope_api.status.contracts import SourceAvailabilityLookup


@dataclass(frozen=True)
class MarineForecastImportReport:
    data_version: str
    ingestion_run_id: str
    request_key: str
    status: str
    records_received: int
    records_accepted: int
    records_rejected: int
    inserted: int
    unchanged: int
    artifact_reference: str


class MarineForecastQueryService:
    def __init__(
        self,
        repository: MarineForecastQueryRepository,
        source_availability: SourceAvailabilityLookup | None = None,
    ) -> None:
        self._repository = repository
        self._source_availability = source_availability

    def query(self, query: MarineForecastQuery) -> MarineForecastQueryResult:
        if query.start_at.tzinfo is None or query.end_at.tzinfo is None:
            raise InvalidQueryError("start_at and end_at must include UTC offsets")
        if query.start_at >= query.end_at:
            raise InvalidQueryError("start_at must be earlier than end_at")
        if query.end_at - query.start_at > timedelta(days=7):
            raise InvalidQueryError("the forecast window cannot exceed 7 days")
        if self._source_availability is None:
            return self._repository.query(query)
        availability = self._source_availability.get_source_availability("open-meteo-marine")
        if availability is None or not availability.has_usable_data:
            raise SourceDataUnavailableError("Open-Meteo marine data is unavailable")
        result = self._repository.query(query)
        return replace(
            result,
            records=tuple(
                replace(
                    record,
                    source_state=availability.state,
                    cache_age_seconds=availability.cache_age_seconds,
                )
                for record in result.records
            ),
        )


class MarineForecastImportService:
    def __init__(
        self,
        session: Session,
        artifact_store: MarineForecastArtifactStore,
        *,
        code_revision: str,
    ) -> None:
        if not code_revision.strip():
            raise ValueError("code_revision cannot be blank")
        self._session = session
        self._artifact_store = artifact_store
        self._code_revision = code_revision.strip()
        self._provenance = ProvenanceService(SqlAlchemyProvenanceRepository(session))
        self._forecasts = SqlAlchemyMarineForecastRepository(session)

    def import_forecast(
        self,
        provider: MarineForecastProvider,
        parser: MarineForecastParser,
        request: MarineForecastRequest,
    ) -> MarineForecastImportReport:
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
            dataset = provider.fetch(request)
        except MarineDataError as error:
            self._record_download_failure(source.id, request, str(error))
            raise

        stored = self._artifact_store.store(dataset)
        version = self._provenance.register_version(
            RegisterSourceVersion(
                source_id=source.id,
                data_version=dataset.data_version,
                schema_version=dataset.schema_version,
                source_url=dataset.source_url,
                published_at=None,
                retrieved_at=dataset.retrieved_at,
                publication_status=PublicationStatus.PRODUCTION,
                checksum_algorithm="sha256",
                checksum=dataset.checksum_sha256,
                artifact_reference=stored.reference,
            )
        )
        run = self._provenance.start_run(
            StartIngestionRun(
                source_id=source.id,
                source_version_id=version.id,
                idempotency_key=(
                    f"marine:{request.request_key[:16]}:{dataset.data_version}:"
                    f"{parser.normalization_version}:{self._code_revision}"
                ),
                source_state=SourceState.LIVE,
                code_revision=self._code_revision,
                started_at=datetime.now(UTC),
                parameters={
                    "request_key": request.request_key,
                    "requested_latitude": request.latitude,
                    "requested_longitude": request.longitude,
                    "forecast_hours": request.forecast_hours,
                    "model": request.model,
                    "variables": list(request.variables),
                    "normalization_version": parser.normalization_version,
                    "artifact_size_bytes": stored.size_bytes,
                },
            )
        )
        if run.status != IngestionStatus.RUNNING.value:
            return _report_from_run(
                run, dataset.data_version, request.request_key, stored.reference
            )

        try:
            parsed = parser.parse(dataset)
        except MarineDataError as error:
            self._fail_schema_run(run.id, str(error))
            raise
        inserted = self._forecasts.insert_forecast(
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
                    message=f"Open-Meteo import reported {code} forecast rows",
                )
            )
        run.parameters = {
            **run.parameters,
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
            completed, dataset.data_version, request.request_key, stored.reference
        )

    def _record_download_failure(
        self, source_id: UUID, request: MarineForecastRequest, reason: str
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
                parameters={"provider": "open-meteo-marine", "request_key": request.request_key},
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
                message="Open-Meteo response schema could not be processed",
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
) -> MarineForecastImportReport:
    return MarineForecastImportReport(
        data_version=data_version,
        ingestion_run_id=str(run.id),
        request_key=request_key,
        status=run.status,
        records_received=run.records_received,
        records_accepted=run.records_accepted,
        records_rejected=run.records_rejected,
        inserted=int(run.parameters.get("inserted", 0)),
        unchanged=int(run.parameters.get("unchanged", 0)),
        artifact_reference=artifact_reference,
    )
