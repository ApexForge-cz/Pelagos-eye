from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from geoalchemy2 import Geometry
from geoalchemy2.elements import WKTElement
from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session

from oceanscope_api.earthquakes.contracts import (
    EarthquakeSearchQuery,
    EarthquakeSearchRecord,
    EarthquakeSearchResult,
    NormalizedEarthquakeEvent,
)
from oceanscope_api.earthquakes.models import EarthquakeEvent
from oceanscope_api.provenance.models import (
    DataSource,
    IngestionRun,
    IngestionStatus,
    RedistributionStatus,
    SourceVersion,
)


@dataclass(frozen=True)
class EarthquakeUpsertResult:
    inserted: int
    updated: int
    unchanged: int
    stale_revisions: int


class SqlAlchemyEarthquakeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_events(
        self,
        *,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        normalization_version: str,
        records: list[NormalizedEarthquakeEvent],
    ) -> EarthquakeUpsertResult:
        event_ids = [record.event_id for record in records]
        existing = {
            event.event_id: event
            for event in self._session.scalars(
                select(EarthquakeEvent).where(EarthquakeEvent.event_id.in_(event_ids))
            )
        }
        inserted = updated = unchanged = stale = 0
        for record in records:
            current = existing.get(record.event_id)
            if current is None:
                self._session.add(
                    EarthquakeEvent(
                        event_id=record.event_id,
                        source_version_id=source_version_id,
                        ingestion_run_id=ingestion_run_id,
                        normalization_version=normalization_version,
                        **_event_values(record),
                    )
                )
                inserted += 1
            elif record.provider_updated_at > current.provider_updated_at:
                current.source_version_id = source_version_id
                current.ingestion_run_id = ingestion_run_id
                current.normalization_version = normalization_version
                for name, value in _event_values(record).items():
                    setattr(current, name, value)
                updated += 1
            elif record.provider_updated_at == current.provider_updated_at:
                unchanged += 1
            else:
                stale += 1
        self._session.flush()
        return EarthquakeUpsertResult(inserted, updated, unchanged, stale)

    def search(self, query: EarthquakeSearchQuery) -> EarthquakeSearchResult:
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
        envelope = func.ST_MakeEnvelope(
            query.min_longitude,
            query.min_latitude,
            query.max_longitude,
            query.max_latitude,
            4326,
        )
        conditions = [
            DataSource.redistribution_status == RedistributionStatus.ALLOWED.value,
            IngestionRun.status.in_(
                (IngestionStatus.SUCCEEDED.value, IngestionStatus.PARTIAL.value)
            ),
            EarthquakeEvent.event_time >= query.start_at,
            EarthquakeEvent.event_time < query.end_at,
            func.ST_Intersects(
                cast(EarthquakeEvent.location, Geometry(geometry_type="POINT", srid=4326)),
                envelope,
            ),
        ]
        if query.min_magnitude is not None:
            conditions.append(EarthquakeEvent.magnitude >= query.min_magnitude)

        joins = (
            select(EarthquakeEvent)
            .join(IngestionRun, IngestionRun.id == EarthquakeEvent.ingestion_run_id)
            .join(SourceVersion, SourceVersion.id == EarthquakeEvent.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(*conditions)
        )
        total = int(
            self._session.scalar(select(func.count()).select_from(joins.order_by(None).subquery()))
            or 0
        )
        statement = (
            select(
                EarthquakeEvent,
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
            .join(IngestionRun, IngestionRun.id == EarthquakeEvent.ingestion_run_id)
            .join(SourceVersion, SourceVersion.id == EarthquakeEvent.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(*conditions)
            .order_by(EarthquakeEvent.event_time.desc(), EarthquakeEvent.event_id)
            .offset(query.offset)
            .limit(query.limit)
        )
        records: list[EarthquakeSearchRecord] = []
        for row in self._session.execute(statement):
            event = row[0]
            ingested_at = row.finished_at
            if ingested_at is None:
                raise RuntimeError("earthquake records must belong to a completed ingestion run")
            records.append(
                EarthquakeSearchRecord(
                    id=event.id,
                    event_id=event.event_id,
                    event_time=event.event_time,
                    provider_updated_at=event.provider_updated_at,
                    longitude=event.longitude,
                    latitude=event.latitude,
                    depth_km=event.depth_km,
                    magnitude=event.magnitude,
                    place=event.place,
                    event_type=event.event_type,
                    provider_status=event.provider_status,
                    tsunami=event.tsunami,
                    significance=event.significance,
                    detail_url=event.detail_url,
                    quality_flags=tuple(event.quality_flags),
                    normalized_at=event.normalized_at,
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
        return EarthquakeSearchResult(records=tuple(records), total=total)


def _event_values(record: NormalizedEarthquakeEvent) -> dict[str, object]:
    return {
        "event_time": record.event_time,
        "provider_updated_at": record.provider_updated_at,
        "longitude": record.longitude,
        "latitude": record.latitude,
        "depth_km": record.depth_km,
        "location": WKTElement(f"POINT({record.longitude} {record.latitude})", srid=4326),
        "magnitude": record.magnitude,
        "place": record.place,
        "event_type": record.event_type,
        "provider_status": record.provider_status,
        "tsunami": record.tsunami,
        "significance": record.significance,
        "detail_url": record.detail_url,
        "quality_flags": record.quality_flags,
        "raw_record": record.raw_record,
    }
