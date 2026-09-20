from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from oceanscope_api.db.session import database_is_available
from oceanscope_api.status.redis import redis_is_available
from oceanscope_api.status.repository import ManagedSqlAlchemySourceStatusRepository
from oceanscope_api.status.service import SourceStatusService, SystemStatusService

router = APIRouter(prefix="/system", tags=["system"])


class DependencyStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    state: Literal["LIVE", "OFFLINE"]
    detail: str


class FreshnessResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    age_seconds: int | None
    live_ttl_seconds: int
    delayed_ttl_seconds: int
    cache_ttl_seconds: int | None


class LatestIngestionRunResponse(BaseModel):
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


class ProviderStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    slug: str
    display_name: str
    state: Literal["LIVE", "CACHED", "DELAYED", "OFFLINE"]
    availability: Literal["AVAILABLE", "DATA UNAVAILABLE"]
    cache_age_seconds: int | None
    freshness: FreshnessResponse
    source_published_at: datetime | None
    source_retrieved_at: datetime | None
    latest_run: LatestIngestionRunResponse | None


class SystemStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    service: Literal["oceanscope-api"]
    version: str
    overall_state: Literal["READY", "DEGRADED"]
    checked_at: datetime
    database: DependencyStatusResponse
    redis: DependencyStatusResponse
    providers: list[ProviderStatusResponse]


def get_system_status_service() -> SystemStatusService:
    source_statuses = SourceStatusService(ManagedSqlAlchemySourceStatusRepository())
    return SystemStatusService(
        database_is_available,
        redis_is_available,
        source_statuses.list_sources,
    )


@router.get("/status", response_model=SystemStatusResponse)
def system_status(
    service: Annotated[SystemStatusService, Depends(get_system_status_service)],
) -> SystemStatusResponse:
    """Report dependency and stored provider health without inventing state."""
    return SystemStatusResponse.model_validate(service.get_status())
