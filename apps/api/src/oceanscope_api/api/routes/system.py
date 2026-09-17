from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from oceanscope_api.db.session import database_is_available
from oceanscope_api.status.service import SystemStatusService

router = APIRouter(prefix="/system", tags=["system"])


class DependencyStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    state: Literal["LIVE", "OFFLINE"]
    detail: str


class SystemStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    service: Literal["oceanscope-api"]
    version: str
    overall_state: Literal["READY", "DEGRADED"]
    checked_at: datetime
    database: DependencyStatusResponse


def get_system_status_service() -> SystemStatusService:
    return SystemStatusService(database_is_available)


@router.get("/status", response_model=SystemStatusResponse)
def system_status(
    service: Annotated[SystemStatusService, Depends(get_system_status_service)],
) -> SystemStatusResponse:
    """Report application and database availability without inventing dependency state."""
    return SystemStatusResponse.model_validate(service.get_status())
