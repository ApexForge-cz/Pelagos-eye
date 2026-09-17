from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session

from oceanscope_api.ocean.contracts import NormalizedMarineForecastPoint
from oceanscope_api.ocean.models import MarineForecastPoint


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
