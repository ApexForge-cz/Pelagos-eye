from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict


class DatabaseUnavailableError(RuntimeError):
    """Raised when a database-backed API cannot safely answer a request."""


class ProblemDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    instance: str
    correlation_id: str | None = None
    errors: list[dict[str, Any]] | None = None


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    problem = ProblemDetail(
        type="https://oceanscope.invalid/problems/request-validation",
        title="Request validation failed",
        status=422,
        detail="The request did not satisfy the endpoint contract.",
        instance=request.url.path,
        correlation_id=getattr(request.state, "correlation_id", None),
        errors=[dict(error) for error in exc.errors()],
    )
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
    )


async def database_unavailable_handler(
    request: Request,
    _: DatabaseUnavailableError,
) -> JSONResponse:
    problem = ProblemDetail(
        type="https://oceanscope.invalid/problems/database-unavailable",
        title="Database unavailable",
        status=503,
        detail="The requested data is currently unavailable.",
        instance=request.url.path,
        correlation_id=getattr(request.state, "correlation_id", None),
    )
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type="application/problem+json",
    )


def install_exception_handlers(application: FastAPI) -> None:
    application.add_exception_handler(RequestValidationError, validation_error_handler)  # type: ignore[arg-type]
    application.add_exception_handler(DatabaseUnavailableError, database_unavailable_handler)  # type: ignore[arg-type]
