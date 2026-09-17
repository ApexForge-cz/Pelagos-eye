from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from oceanscope_api.core.errors import SourceDataUnavailableError
from oceanscope_api.ports.artifacts import LocalArtifactStore
from oceanscope_api.ports.contracts import (
    PortDataError,
    PortDatasetParser,
    PortDatasetProvider,
    PortSearchQuery,
    PortSearchRepository,
    PortSearchResult,
)
from oceanscope_api.ports.repository import SqlAlchemyPortRepository
from oceanscope_api.provenance.models import IngestionStatus, QualitySeverity, SourceState
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
class PortImportReport:
    source_slug: str
    data_version: str
    ingestion_run_id: str
    status: str
    records_received: int
    records_accepted: int
    records_rejected: int
    records_skipped: int
    artifact_reference: str


class PortSearchService:
    def __init__(
        self,
        repository: PortSearchRepository,
        source_availability: SourceAvailabilityLookup | None = None,
    ) -> None:
        self._repository = repository
        self._source_availability = source_availability

    def search(self, query: PortSearchQuery) -> PortSearchResult:
        normalized = PortSearchQuery(
            text=query.text.strip() if query.text is not None else None,
            country_code=(
                query.country_code.strip().upper() if query.country_code is not None else None
            ),
            has_coordinates=query.has_coordinates,
            limit=query.limit,
            offset=query.offset,
        )
        if self._source_availability is None:
            return self._repository.search(normalized)
        availability = self._source_availability.get_source_availability("unece-unlocode")
        if availability is None or not availability.has_usable_data:
            raise SourceDataUnavailableError("UNECE UN/LOCODE data is unavailable")
        result = self._repository.search(normalized)
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


class PortImportService:
    def __init__(
        self,
        session: Session,
        artifact_store: LocalArtifactStore,
        *,
        code_revision: str,
    ) -> None:
        if not code_revision.strip():
            raise ValueError("code_revision cannot be blank")
        self._session = session
        self._artifact_store = artifact_store
        self._code_revision = code_revision.strip()
        self._provenance = ProvenanceService(SqlAlchemyProvenanceRepository(session))
        self._ports = SqlAlchemyPortRepository(session)

    def import_dataset(
        self,
        provider: PortDatasetProvider,
        parser: PortDatasetParser,
    ) -> PortImportReport:
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
            dataset = provider.fetch()
        except PortDataError as error:
            now = datetime.now(UTC)
            failed_run = self._provenance.start_run(
                StartIngestionRun(
                    source_id=source.id,
                    source_version_id=None,
                    idempotency_key=f"download-failure:{now.isoformat()}",
                    source_state=SourceState.OFFLINE,
                    code_revision=self._code_revision,
                    started_at=now,
                    parameters={"provider": provider.source.slug},
                )
            )
            self._provenance.complete_run(
                CompleteIngestionRun(
                    run_id=failed_run.id,
                    status=IngestionStatus.FAILED,
                    finished_at=datetime.now(UTC),
                    records_received=0,
                    records_accepted=0,
                    records_rejected=0,
                    failure_reason=str(error),
                )
            )
            self._session.commit()
            raise

        stored = self._artifact_store.store(dataset)
        version = self._provenance.register_version(
            RegisterSourceVersion(
                source_id=source.id,
                data_version=dataset.data_version,
                schema_version=dataset.schema_version,
                source_url=dataset.source_url,
                published_at=dataset.published_at,
                retrieved_at=dataset.retrieved_at,
                publication_status=dataset.publication_status,
                checksum_algorithm="sha256",
                checksum=stored.checksum_sha256,
                artifact_reference=stored.reference,
            )
        )
        run = self._provenance.start_run(
            StartIngestionRun(
                source_id=source.id,
                source_version_id=version.id,
                idempotency_key=(
                    f"port-import:{dataset.data_version}:{parser.normalization_version}:"
                    f"{self._code_revision}"
                ),
                source_state=SourceState.LIVE,
                code_revision=self._code_revision,
                started_at=datetime.now(UTC),
                parameters={
                    "provider": provider.source.slug,
                    "normalization_version": parser.normalization_version,
                    "artifact_size_bytes": stored.size_bytes,
                },
            )
        )
        if run.status != IngestionStatus.RUNNING.value:
            return PortImportReport(
                source_slug=provider.source.slug,
                data_version=dataset.data_version,
                ingestion_run_id=str(run.id),
                status=run.status,
                records_received=run.records_received,
                records_accepted=run.records_accepted,
                records_rejected=run.records_rejected,
                records_skipped=int(run.parameters.get("records_skipped", 0)),
                artifact_reference=stored.reference,
            )

        try:
            parsed = parser.parse(dataset)
        except PortDataError as error:
            self._provenance.record_quality_issue(
                RecordQualityIssue(
                    run_id=run.id,
                    code="provider_revision",
                    severity=QualitySeverity.ERROR,
                    record_count=1,
                    message="Official port dataset schema could not be processed",
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
                    failure_reason=str(error),
                )
            )
            self._session.commit()
            raise

        self._ports.replace_version_records(
            source_version_id=version.id,
            ingestion_run_id=run.id,
            normalization_version=parser.normalization_version,
            records=parsed.records,
        )
        for code, count in sorted(parsed.quality_counts.items()):
            self._provenance.record_quality_issue(
                RecordQualityIssue(
                    run_id=run.id,
                    code=code,
                    severity=(
                        QualitySeverity.ERROR
                        if code in {"missing_required", "provider_revision"}
                        else QualitySeverity.WARNING
                    ),
                    record_count=count,
                    message=f"Port import reported {code} records",
                )
            )

        run.parameters = {
            **run.parameters,
            "records_skipped": parsed.records_skipped,
        }
        final_status = (
            IngestionStatus.PARTIAL
            if parsed.records_rejected or parsed.quality_counts
            else IngestionStatus.SUCCEEDED
        )
        completed = self._provenance.complete_run(
            CompleteIngestionRun(
                run_id=run.id,
                status=final_status,
                finished_at=datetime.now(UTC),
                records_received=parsed.records_received,
                records_accepted=len(parsed.records),
                records_rejected=parsed.records_rejected,
            )
        )
        self._session.commit()
        return PortImportReport(
            source_slug=provider.source.slug,
            data_version=dataset.data_version,
            ingestion_run_id=str(completed.id),
            status=completed.status,
            records_received=completed.records_received,
            records_accepted=completed.records_accepted,
            records_rejected=completed.records_rejected,
            records_skipped=parsed.records_skipped,
            artifact_reference=stored.reference,
        )
