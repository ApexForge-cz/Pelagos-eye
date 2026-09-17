from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from oceanscope_api.db.session import get_session
from oceanscope_api.status.repository import SqlAlchemySourceStatusRepository
from oceanscope_api.status.service import SourceStatusService

router = APIRouter(prefix="/data", tags=["data"])


class QualityIssueResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    code: str
    severity: Literal["info", "warning", "error"]
    record_count: int
    message: str


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: UUID
    status: Literal["running", "succeeded", "partial", "failed"]
    source_state: Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
    cache_age_seconds: int | None
    started_at: datetime
    finished_at: datetime | None
    records_received: int
    records_accepted: int
    records_rejected: int


class SourceVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    data_version: str
    schema_version: str
    source_url: str
    published_at: datetime | None
    retrieved_at: datetime


class SourceStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    slug: str
    display_name: str
    official_url: str
    terms_url: str | None
    attribution_text: str
    license_identifier: str | None
    redistribution_status: Literal["allowed", "restricted", "prohibited", "unreviewed"]
    state: Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
    availability: Literal["AVAILABLE", "DATA UNAVAILABLE"]
    has_usable_data: bool
    latest_run: IngestionRunResponse | None
    latest_usable_run: IngestionRunResponse | None
    latest_version: SourceVersionResponse | None
    quality_issues: list[QualityIssueResponse]


class SourceCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: datetime
    sources: list[SourceStatusResponse]


def get_source_status_service(
    session: Annotated[Session, Depends(get_session)],
) -> SourceStatusService:
    return SourceStatusService(SqlAlchemySourceStatusRepository(session))


@router.get("/sources", response_model=SourceCatalogResponse)
def list_sources(
    service: Annotated[SourceStatusService, Depends(get_source_status_service)],
) -> SourceCatalogResponse:
    """Return source provenance and current/last-usable ingestion states."""
    sources = [SourceStatusResponse.model_validate(source) for source in service.list_sources()]
    return SourceCatalogResponse(generated_at=datetime.now(UTC), sources=sources)
