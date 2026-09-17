from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from oceanscope_api.db.session import get_session
from oceanscope_api.ports.contracts import PortSearchQuery
from oceanscope_api.ports.repository import SqlAlchemyPortRepository
from oceanscope_api.ports.service import PortSearchService
from oceanscope_api.status.repository import SqlAlchemySourceStatusRepository
from oceanscope_api.status.service import SourceStatusService

router = APIRouter(prefix="/ports", tags=["ports"])


class PortProvenanceResponse(BaseModel):
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


class PortRecordResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    source_record_id: str
    record_type: Literal["unlocode", "wpi"]
    name: str
    country_code: str
    un_locode: str | None
    longitude: float | None
    latitude: float | None
    coordinate_accuracy: str | None
    function_code: str | None
    source_status: str | None
    source_updated_value: str | None
    quality_flags: list[str]
    provenance: PortProvenanceResponse


class PortSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    total: int
    limit: int
    offset: int
    records: list[PortRecordResponse]


def get_port_search_service(
    session: Annotated[Session, Depends(get_session)],
) -> PortSearchService:
    return PortSearchService(
        SqlAlchemyPortRepository(session),
        SourceStatusService(SqlAlchemySourceStatusRepository(session)),
    )


@router.get("", response_model=PortSearchResponse)
def search_ports(
    service: Annotated[PortSearchService, Depends(get_port_search_service)],
    q: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    country_code: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
    has_coordinates: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> PortSearchResponse:
    """Search bounded, publishable port-reference records with full provenance."""
    result = service.search(
        PortSearchQuery(
            text=q,
            country_code=country_code,
            has_coordinates=has_coordinates,
            limit=limit,
            offset=offset,
        )
    )
    return PortSearchResponse(
        generated_at=datetime.now(UTC),
        total=result.total,
        limit=limit,
        offset=offset,
        records=[
            PortRecordResponse(
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
                quality_flags=list(record.quality_flags),
                provenance=PortProvenanceResponse.model_validate(record),
            )
            for record in result.records
        ],
    )
