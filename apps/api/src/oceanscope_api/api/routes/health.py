from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from oceanscope_api import __version__

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: Literal["oceanscope-api"] = "oceanscope-api"
    version: str
    status: Literal["ok", "ready"]
    checked_at: datetime


def _health(status: Literal["ok", "ready"]) -> HealthResponse:
    return HealthResponse(version=__version__, status=status, checked_at=datetime.now(UTC))


@router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Report that the API process is running."""
    return _health("ok")


@router.get("/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    """Report Phase 1 readiness; dependency checks are added with their integrations."""
    return _health("ready")
