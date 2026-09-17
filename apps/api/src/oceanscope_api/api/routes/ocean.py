from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from oceanscope_api.db.session import get_session
from oceanscope_api.ocean.contracts import MarineForecastQuery
from oceanscope_api.ocean.repository import SqlAlchemyMarineForecastRepository
from oceanscope_api.ocean.service import MarineForecastQueryService
from oceanscope_api.status.repository import SqlAlchemySourceStatusRepository
from oceanscope_api.status.service import SourceStatusService

router = APIRouter(prefix="/ocean", tags=["ocean"])

FORECAST_WARNING = (
    "Model forecast with coastal limitations; not for navigation, collision avoidance, "
    "or emergency decisions."
)


class MarineForecastProvenanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    source_slug: str
    source_display_name: str
    source_url: str
    attribution_text: str
    data_version: str
    schema_version: str
    published_at: datetime | None
    retrieved_at: datetime
    ingested_at: datetime
    normalized_at: datetime
    source_state: Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
    cache_age_seconds: int | None


class MarineForecastRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    requested_latitude: float
    requested_longitude: float
    grid_latitude: float
    grid_longitude: float
    valid_at: datetime
    model: str
    wave_height_m: float | None
    wave_direction_deg: float | None
    wave_period_s: float | None
    sea_surface_temperature_c: float | None
    ocean_current_velocity_kmh: float | None
    ocean_current_direction_deg: float | None
    sea_level_height_msl_m: float | None
    units: dict[str, str]
    quality_flags: list[str]
    provenance: MarineForecastProvenanceResponse


class MarineForecastQueryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    coverage: str
    warning: str
    total: int
    limit: int
    offset: int
    records: list[MarineForecastRecordResponse]


def get_marine_forecast_query_service(
    session: Annotated[Session, Depends(get_session)],
) -> MarineForecastQueryService:
    return MarineForecastQueryService(
        SqlAlchemyMarineForecastRepository(session),
        SourceStatusService(SqlAlchemySourceStatusRepository(session)),
    )


@router.get("/forecast", response_model=MarineForecastQueryResponse)
def query_marine_forecast(
    service: Annotated[MarineForecastQueryService, Depends(get_marine_forecast_query_service)],
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    start_at: datetime,
    end_at: datetime,
    limit: Annotated[int, Query(ge=1, le=168)] = 168,
    offset: Annotated[int, Query(ge=0, le=1000)] = 0,
) -> MarineForecastQueryResponse:
    """Return the latest stored forecast for a requested point and bounded time window."""
    result = service.query(
        MarineForecastQuery(
            latitude=latitude,
            longitude=longitude,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
            offset=offset,
        )
    )
    return MarineForecastQueryResponse(
        generated_at=datetime.now(UTC),
        coverage="Latest stored Open-Meteo forecast matching the requested coordinate",
        warning=FORECAST_WARNING,
        total=result.total,
        limit=limit,
        offset=offset,
        records=[
            MarineForecastRecordResponse(
                id=record.id,
                requested_latitude=record.requested_latitude,
                requested_longitude=record.requested_longitude,
                grid_latitude=record.grid_latitude,
                grid_longitude=record.grid_longitude,
                valid_at=record.valid_at,
                model=record.model,
                wave_height_m=record.wave_height_m,
                wave_direction_deg=record.wave_direction_deg,
                wave_period_s=record.wave_period_s,
                sea_surface_temperature_c=record.sea_surface_temperature_c,
                ocean_current_velocity_kmh=record.ocean_current_velocity_kmh,
                ocean_current_direction_deg=record.ocean_current_direction_deg,
                sea_level_height_msl_m=record.sea_level_height_msl_m,
                units=dict(record.units),
                quality_flags=list(record.quality_flags),
                provenance=MarineForecastProvenanceResponse.model_validate(record),
            )
            for record in result.records
        ],
    )
