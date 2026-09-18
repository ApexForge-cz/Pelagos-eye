from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from oceanscope_api.db.session import get_session
from oceanscope_api.earthquakes.contracts import EarthquakeSearchQuery
from oceanscope_api.earthquakes.repository import SqlAlchemyEarthquakeRepository
from oceanscope_api.earthquakes.service import EarthquakeSearchService
from oceanscope_api.status.repository import SqlAlchemySourceStatusRepository
from oceanscope_api.status.service import SourceStatusService

router = APIRouter(prefix="/earthquakes", tags=["earthquakes"])

TSUNAMI_WARNING = (
    "The tsunami field is USGS provider metadata, not an OceanScope impact prediction or warning."
)


class EarthquakeProvenanceResponse(BaseModel):
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


class EarthquakeRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    event_id: str
    event_time: datetime
    provider_updated_at: datetime
    longitude: float
    latitude: float
    depth_km: float
    magnitude: float | None
    place: str | None
    event_type: str | None
    provider_status: str | None
    tsunami: bool
    significance: int | None
    detail_url: str | None
    quality_flags: list[str]
    provenance: EarthquakeProvenanceResponse


class EarthquakeSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    coverage: str
    warning: str
    total: int
    limit: int
    offset: int
    records: list[EarthquakeRecordResponse]


def get_earthquake_search_service(
    session: Annotated[Session, Depends(get_session)],
) -> EarthquakeSearchService:
    return EarthquakeSearchService(
        SqlAlchemyEarthquakeRepository(session),
        SourceStatusService(SqlAlchemySourceStatusRepository(session)),
    )


@router.get("", response_model=EarthquakeSearchResponse)
def search_earthquakes(
    service: Annotated[EarthquakeSearchService, Depends(get_earthquake_search_service)],
    start_at: datetime,
    end_at: datetime,
    min_longitude: Annotated[float, Query(ge=-180, le=180)],
    min_latitude: Annotated[float, Query(ge=-90, le=90)],
    max_longitude: Annotated[float, Query(ge=-180, le=180)],
    max_latitude: Annotated[float, Query(ge=-90, le=90)],
    min_magnitude: Annotated[float | None, Query(ge=-10, le=10)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> EarthquakeSearchResponse:
    """Return bounded USGS earthquake records with revision and provenance timestamps."""
    result = service.search(
        EarthquakeSearchQuery(
            start_at=start_at,
            end_at=end_at,
            min_longitude=min_longitude,
            min_latitude=min_latitude,
            max_longitude=max_longitude,
            max_latitude=max_latitude,
            min_magnitude=min_magnitude,
            limit=limit,
            offset=offset,
        )
    )
    return EarthquakeSearchResponse(
        generated_at=datetime.now(UTC),
        coverage="Stored snapshots from the USGS all-earthquakes past-hour feed",
        warning=TSUNAMI_WARNING,
        total=result.total,
        limit=limit,
        offset=offset,
        records=[
            EarthquakeRecordResponse(
                id=record.id,
                event_id=record.event_id,
                event_time=record.event_time,
                provider_updated_at=record.provider_updated_at,
                longitude=record.longitude,
                latitude=record.latitude,
                depth_km=record.depth_km,
                magnitude=record.magnitude,
                place=record.place,
                event_type=record.event_type,
                provider_status=record.provider_status,
                tsunami=record.tsunami,
                significance=record.significance,
                detail_url=record.detail_url,
                quality_flags=list(record.quality_flags),
                provenance=EarthquakeProvenanceResponse.model_validate(record),
            )
            for record in result.records
        ],
    )
