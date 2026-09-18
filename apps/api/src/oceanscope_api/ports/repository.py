from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import Select, cast, delete, func, or_, select
from sqlalchemy.orm import Session

from oceanscope_api.ports.contracts import (
    NormalizedPortSourceRecord,
    PortSearchQuery,
    PortSearchRecord,
    PortSearchResult,
)
from oceanscope_api.ports.models import PortSourceRecord
from oceanscope_api.provenance.models import (
    DataSource,
    IngestionRun,
    IngestionStatus,
    RedistributionStatus,
    SourceVersion,
)


class SqlAlchemyPortRepository:
    """Persist provider-specific port records without merging source identities."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def count_for_version(self, source_version_id: UUID) -> int:
        statement = (
            select(func.count())
            .select_from(PortSourceRecord)
            .where(PortSourceRecord.source_version_id == source_version_id)
        )
        return int(self._session.scalar(statement) or 0)

    def replace_version_records(
        self,
        *,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        normalization_version: str,
        records: Sequence[NormalizedPortSourceRecord],
    ) -> None:
        self._session.execute(
            delete(PortSourceRecord).where(PortSourceRecord.source_version_id == source_version_id)
        )
        normalized_at = datetime.now(UTC)
        entities = [
            PortSourceRecord(
                id=uuid4(),
                source_version_id=source_version_id,
                ingestion_run_id=ingestion_run_id,
                source_record_key=record.source_record_key,
                source_record_id=record.source_record_id,
                record_type=record.record_type,
                name=record.name,
                country_code=record.country_code,
                un_locode=record.un_locode,
                longitude=record.longitude,
                latitude=record.latitude,
                location=_location(record),
                coordinate_accuracy=record.coordinate_accuracy,
                function_code=record.function_code,
                source_status=record.source_status,
                source_updated_value=record.source_updated_value,
                normalization_version=normalization_version,
                quality_flags=list(record.quality_flags),
                raw_record=dict(record.raw_record),
                normalized_at=normalized_at,
            )
            for record in records
        ]
        self._session.add_all(entities)
        self._session.flush()

    def search(self, query: PortSearchQuery) -> PortSearchResult:
        latest_usable_run_id = (
            select(IngestionRun.id)
            .where(
                IngestionRun.data_source_id == DataSource.id,
                IngestionRun.status.in_(
                    (IngestionStatus.SUCCEEDED.value, IngestionStatus.PARTIAL.value)
                ),
                IngestionRun.source_version_id.is_not(None),
            )
            .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
            .limit(1)
            .correlate(DataSource)
            .scalar_subquery()
        )
        latest_source_state = (
            select(IngestionRun.source_state)
            .where(IngestionRun.data_source_id == DataSource.id)
            .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
            .limit(1)
            .correlate(DataSource)
            .scalar_subquery()
        )
        latest_cache_age = (
            select(IngestionRun.cache_age_seconds)
            .where(IngestionRun.data_source_id == DataSource.id)
            .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
            .limit(1)
            .correlate(DataSource)
            .scalar_subquery()
        )
        conditions = [
            DataSource.redistribution_status == RedistributionStatus.ALLOWED.value,
            IngestionRun.id == latest_usable_run_id,
        ]
        if query.text is not None:
            search_text = query.text.strip()
            conditions.append(
                or_(
                    PortSourceRecord.name.icontains(search_text, autoescape=True),
                    PortSourceRecord.un_locode.icontains(search_text, autoescape=True),
                )
            )
        if query.country_code is not None:
            conditions.append(PortSourceRecord.country_code == query.country_code)
        if query.has_coordinates is True:
            conditions.append(PortSourceRecord.location.is_not(None))
        elif query.has_coordinates is False:
            conditions.append(PortSourceRecord.location.is_(None))
        if query.min_longitude is not None:
            envelope = func.ST_MakeEnvelope(
                query.min_longitude,
                query.min_latitude,
                query.max_longitude,
                query.max_latitude,
                4326,
            )
            conditions.append(
                func.ST_Intersects(
                    cast(PortSourceRecord.location, Geometry(geometry_type="POINT", srid=4326)),
                    envelope,
                )
            )

        base = (
            select(PortSourceRecord)
            .join(IngestionRun, IngestionRun.id == PortSourceRecord.ingestion_run_id)
            .join(SourceVersion, SourceVersion.id == PortSourceRecord.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(*conditions)
        )
        total = int(self._session.scalar(_count_statement(base)) or 0)
        statement = (
            select(
                PortSourceRecord,
                DataSource.slug,
                DataSource.display_name,
                DataSource.attribution_text,
                SourceVersion.source_url,
                SourceVersion.data_version,
                SourceVersion.schema_version,
                SourceVersion.published_at,
                SourceVersion.retrieved_at,
                IngestionRun.finished_at,
                latest_source_state.label("latest_source_state"),
                latest_cache_age.label("latest_cache_age"),
            )
            .join(IngestionRun, IngestionRun.id == PortSourceRecord.ingestion_run_id)
            .join(SourceVersion, SourceVersion.id == PortSourceRecord.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(*conditions)
            .order_by(
                PortSourceRecord.name,
                PortSourceRecord.country_code,
                PortSourceRecord.source_record_id,
            )
            .offset(query.offset)
            .limit(query.limit)
        )
        records: list[PortSearchRecord] = []
        for row in self._session.execute(statement):
            record = row[0]
            ingested_at = row.finished_at
            if ingested_at is None:
                raise RuntimeError("usable port records must belong to a completed ingestion run")
            records.append(
                PortSearchRecord(
                    id=record.id,
                    source_record_id=record.source_record_id,
                    record_type=record.record_type,
                    name=record.name,
                    country_code=record.country_code,
                    un_locode=record.un_locode,
                    longitude=record.longitude,
                    latitude=record.latitude,
                    coordinate_accuracy=record.coordinate_accuracy,
                    function_code=record.function_code,
                    source_status=record.source_status,
                    source_updated_value=record.source_updated_value,
                    quality_flags=tuple(record.quality_flags),
                    normalized_at=record.normalized_at,
                    source_slug=row.slug,
                    source_display_name=row.display_name,
                    source_url=row.source_url,
                    attribution_text=row.attribution_text,
                    data_version=row.data_version,
                    schema_version=row.schema_version,
                    published_at=row.published_at,
                    retrieved_at=row.retrieved_at,
                    ingested_at=ingested_at,
                    source_state=row.latest_source_state,
                    cache_age_seconds=row.latest_cache_age,
                )
            )
        return PortSearchResult(records=tuple(records), total=total)


def _location(record: NormalizedPortSourceRecord) -> WKTElement | None:
    if record.longitude is None or record.latitude is None:
        return None
    return WKTElement(f"POINT ({record.longitude} {record.latitude})", srid=4326)


def _count_statement(statement: Select[tuple[PortSourceRecord]]) -> Select[tuple[int]]:
    return select(func.count()).select_from(statement.order_by(None).subquery())
