from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oceanscope_api import __version__
from oceanscope_api.api.routes.health import router as health_router
from oceanscope_api.core.errors import install_exception_handlers
from oceanscope_api.core.logging import CorrelationIdMiddleware, configure_logging
from oceanscope_api.core.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level, settings.environment)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="OceanScope API",
        summary="Engineering foundation for OceanScope",
        version=__version__,
        lifespan=lifespan,
    )
    application.add_middleware(CorrelationIdMiddleware)

    if settings.cors_origin_list:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["Content-Type", "X-Correlation-ID"],
        )

    install_exception_handlers(application)
    application.include_router(health_router)
    return application


app = create_app()
