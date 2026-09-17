from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from oceanscope_api.ocean.contracts import (
    MarineForecastQuery,
    MarineForecastQueryResult,
    MarineForecastRecord,
    NormalizedMarineForecastPoint,
)
from oceanscope_api.ocean.models import MarineForecastPoint
from oceanscope_api.provenance.models import (
    DataSource,
    IngestionRun,
    IngestionStatus,
    RedistributionStatus,
    SourceVersion,
)


@dataclass(frozen=True)
class MarineForecastInsertResult:
    inserted: int
    unchanged: int


class SqlAlchemyMarineForecastRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_forecast(
        self,
        *,
        source_version_id: UUID,
        ingestion_run_id: UUID,
        request_key: str,
        normalization_version: str,
        records: tuple[NormalizedMarineForecastPoint, ...],
    ) -> MarineForecastInsertResult:
        existing_times = set(
            self._session.scalars(
                select(MarineForecastPoint.valid_at).where(
                    MarineForecastPoint.source_version_id == source_version_id,
                    MarineForecastPoint.request_key == request_key,
                )
            )
        )
        inserted = 0
        for record in records:
            if record.valid_at in existing_times:
                continue
            self._session.add(
                MarineForecastPoint(
                    source_version_id=source_version_id,
                    ingestion_run_id=ingestion_run_id,
                    request_key=request_key,
                    normalization_version=normalization_version,
                    requested_latitude=record.requested_latitude,
                    requested_longitude=record.requested_longitude,
                    grid_latitude=record.grid_latitude,
                    grid_longitude=record.grid_longitude,
                    location=WKTElement(
                        f"POINT({record.grid_longitude} {record.grid_latitude})", srid=4326
                    ),
                    valid_at=record.valid_at,
                    model=record.model,
                    wave_height_m=record.wave_height_m,
                    wave_direction_deg=record.wave_direction_deg,
                    wave_period_s=record.wave_period_s,
                    sea_surface_temperature_c=record.sea_surface_temperature_c,
                    ocean_current_velocity_kmh=record.ocean_current_velocity_kmh,
                    ocean_current_direction_deg=record.ocean_current_direction_deg,
                    sea_level_height_msl_m=record.sea_level_height_msl_m,
                    units=record.units,
                    quality_flags=list(record.quality_flags),
                    raw_record=record.raw_record,
                )
            )
            inserted += 1
        self._session.flush()
        return MarineForecastInsertResult(inserted=inserted, unchanged=len(records) - inserted)

    def query(self, query: MarineForecastQuery) -> MarineForecastQueryResult:
        matching_run_id = (
            select(IngestionRun.id)
            .join(
                MarineForecastPoint,
                MarineForecastPoint.ingestion_run_id == IngestionRun.id,
            )
            .join(SourceVersion, SourceVersion.id == MarineForecastPoint.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(
                DataSource.redistribution_status == RedistributionStatus.ALLOWED.value,
                IngestionRun.status.in_(
                    (IngestionStatus.SUCCEEDED.value, IngestionStatus.PARTIAL.value)
                ),
                func.abs(MarineForecastPoint.requested_latitude - query.latitude) <= 0.000001,
                func.abs(MarineForecastPoint.requested_longitude - query.longitude) <= 0.000001,
            )
            .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
            .limit(1)
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
            IngestionRun.id == matching_run_id,
            MarineForecastPoint.valid_at >= query.start_at,
            MarineForecastPoint.valid_at < query.end_at,
        ]
        base = (
            select(MarineForecastPoint)
            .join(IngestionRun, IngestionRun.id == MarineForecastPoint.ingestion_run_id)
            .join(SourceVersion, SourceVersion.id == MarineForecastPoint.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(*conditions)
        )
        total = int(
            self._session.scalar(select(func.count()).select_from(base.order_by(None).subquery()))
            or 0
        )
        statement = (
            select(
                MarineForecastPoint,
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
            .join(IngestionRun, IngestionRun.id == MarineForecastPoint.ingestion_run_id)
            .join(SourceVersion, SourceVersion.id == MarineForecastPoint.source_version_id)
            .join(DataSource, DataSource.id == SourceVersion.data_source_id)
            .where(*conditions)
            .order_by(MarineForecastPoint.valid_at, MarineForecastPoint.id)
            .offset(query.offset)
            .limit(query.limit)
        )
        records: list[MarineForecastRecord] = []
        for row in self._session.execute(statement):
            point = row[0]
            ingested_at = row.finished_at
            if ingested_at is None:
                raise RuntimeError("forecast records must belong to a completed ingestion run")
            records.append(
                MarineForecastRecord(
                    id=point.id,
                    requested_latitude=point.requested_latitude,
                    requested_longitude=point.requested_longitude,
                    grid_latitude=point.grid_latitude,
                    grid_longitude=point.grid_longitude,
                    valid_at=point.valid_at,
                    model=point.model,
                    wave_height_m=point.wave_height_m,
                    wave_direction_deg=point.wave_direction_deg,
                    wave_period_s=point.wave_period_s,
                    sea_surface_temperature_c=point.sea_surface_temperature_c,
                    ocean_current_velocity_kmh=point.ocean_current_velocity_kmh,
                    ocean_current_direction_deg=point.ocean_current_direction_deg,
                    sea_level_height_msl_m=point.sea_level_height_msl_m,
                    units=dict(point.units),
                    quality_flags=tuple(point.quality_flags),
                    normalized_at=point.normalized_at,
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
        return MarineForecastQueryResult(records=tuple(records), total=total)
