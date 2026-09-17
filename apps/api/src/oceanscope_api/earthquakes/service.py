from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from oceanscope_api.core.errors import InvalidQueryError, SourceDataUnavailableError
from oceanscope_api.earthquakes.artifacts import EarthquakeArtifactStore
from oceanscope_api.earthquakes.contracts import (
    EarthquakeDataError,
    EarthquakeFeedParser,
    EarthquakeFeedProvider,
    EarthquakeSearchQuery,
    EarthquakeSearchRepository,
    EarthquakeSearchResult,
)
from oceanscope_api.earthquakes.repository import SqlAlchemyEarthquakeRepository
from oceanscope_api.ports.contracts import PortDataError
from oceanscope_api.provenance.models import (
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
class EarthquakeImportReport:
    data_version: str
    ingestion_run_id: str
    status: str
    records_received: int
    records_accepted: int
    records_rejected: int
    inserted: int
    updated: int
    unchanged: int
    stale_revisions: int
    artifact_reference: str


class EarthquakeSearchService:
    def __init__(
        self,
        repository: EarthquakeSearchRepository,
        source_availability: SourceAvailabilityLookup | None = None,
    ) -> None:
        self._repository = repository
        self._source_availability = source_availability

    def search(self, query: EarthquakeSearchQuery) -> EarthquakeSearchResult:
        if query.start_at.tzinfo is None or query.end_at.tzinfo is None:
            raise InvalidQueryError("start_at and end_at must include UTC offsets")
        if query.start_at >= query.end_at:
            raise InvalidQueryError("start_at must be earlier than end_at")
        if query.end_at - query.start_at > timedelta(days=31):
            raise InvalidQueryError("the time window cannot exceed 31 days")
        if query.min_longitude >= query.max_longitude:
            raise InvalidQueryError("min_longitude must be less than max_longitude")
        if query.min_latitude >= query.max_latitude:
            raise InvalidQueryError("min_latitude must be less than max_latitude")
        if self._source_availability is None:
            return self._repository.search(query)
        availability = self._source_availability.get_source_availability("usgs-earthquakes")
        if availability is None or not availability.has_usable_data:
            raise SourceDataUnavailableError("USGS earthquake data is unavailable")
        result = self._repository.search(query)
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


class EarthquakeImportService:
    def __init__(
        self,
        session: Session,
        artifact_store: EarthquakeArtifactStore,
        *,
        code_revision: str,
    ) -> None:
        if not code_revision.strip():
            raise ValueError("code_revision cannot be blank")
        self._session = session
        self._artifact_store = artifact_store
        self._code_revision = code_revision.strip()
        self._provenance = ProvenanceService(SqlAlchemyProvenanceRepository(session))
        self._events = SqlAlchemyEarthquakeRepository(session)

    def import_feed(
        self,
        provider: EarthquakeFeedProvider,
        parser: EarthquakeFeedParser,
    ) -> EarthquakeImportReport:
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
        except (EarthquakeDataError, PortDataError) as error:
            self._record_download_failure(source.id, str(error))
            raise

        stored = self._artifact_store.store(dataset)
        version = self._provenance.register_version(
            RegisterSourceVersion(
                source_id=source.id,
                data_version=dataset.data_version,
                schema_version=dataset.schema_version,
                source_url=dataset.source_url,
                published_at=dataset.generated_at,
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
                    f"earthquake-import:{dataset.data_version}:"
                    f"{parser.normalization_version}:{self._code_revision}"
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
            return _report_from_run(run, dataset.data_version, stored.reference)

        try:
            parsed = parser.parse(dataset)
        except EarthquakeDataError as error:
            self._fail_schema_run(run.id, str(error))
            raise

        upsert = self._events.upsert_events(
            source_version_id=version.id,
            ingestion_run_id=run.id,
            normalization_version=parser.normalization_version,
            records=parsed.records,
        )
        quality_counts = dict(parsed.quality_counts)
        if upsert.stale_revisions:
            quality_counts["late_arrival"] = upsert.stale_revisions
        for code, count in sorted(quality_counts.items()):
            self._provenance.record_quality_issue(
                RecordQualityIssue(
                    run_id=run.id,
                    code=code,
                    severity=QualitySeverity.WARNING,
                    record_count=count,
                    message=f"USGS import reported {code} records",
                )
            )
        run.parameters = {
            **run.parameters,
            "inserted": upsert.inserted,
            "updated": upsert.updated,
            "unchanged": upsert.unchanged,
            "stale_revisions": upsert.stale_revisions,
        }
        status = (
            IngestionStatus.PARTIAL
            if parsed.records_rejected or quality_counts
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
        return _report_from_run(completed, dataset.data_version, stored.reference)

    def _record_download_failure(self, source_id: object, reason: str) -> None:
        from uuid import UUID

        assert isinstance(source_id, UUID)
        now = datetime.now(UTC)
        run = self._provenance.start_run(
            StartIngestionRun(
                source_id=source_id,
                source_version_id=None,
                idempotency_key=f"download-failure:{now.isoformat()}",
                source_state=SourceState.OFFLINE,
                code_revision=self._code_revision,
                started_at=now,
                parameters={"provider": "usgs-earthquakes"},
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

    def _fail_schema_run(self, run_id: object, reason: str) -> None:
        from uuid import UUID

        assert isinstance(run_id, UUID)
        self._provenance.record_quality_issue(
            RecordQualityIssue(
                run_id=run_id,
                code="provider_revision",
                severity=QualitySeverity.ERROR,
                record_count=1,
                message="USGS feed schema could not be processed",
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
    run: object, data_version: str, artifact_reference: str
) -> EarthquakeImportReport:
    from oceanscope_api.provenance.models import IngestionRun

    assert isinstance(run, IngestionRun)
    return EarthquakeImportReport(
        data_version=data_version,
        ingestion_run_id=str(run.id),
        status=run.status,
        records_received=run.records_received,
        records_accepted=run.records_accepted,
        records_rejected=run.records_rejected,
        inserted=int(run.parameters.get("inserted", 0)),
        updated=int(run.parameters.get("updated", 0)),
        unchanged=int(run.parameters.get("unchanged", 0)),
        stale_revisions=int(run.parameters.get("stale_revisions", 0)),
        artifact_reference=artifact_reference,
    )
