import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from oceanscope_api import __version__
from oceanscope_api.api.routes.data import router as data_router
from oceanscope_api.api.routes.earthquakes import router as earthquakes_router
from oceanscope_api.api.routes.health import router as health_router
from oceanscope_api.api.routes.live_ais import router as live_ais_router
from oceanscope_api.api.routes.ocean import router as ocean_router
from oceanscope_api.api.routes.ports import router as ports_router
from oceanscope_api.api.routes.system import router as system_router
from oceanscope_api.core.errors import install_exception_handlers
from oceanscope_api.core.logging import CorrelationIdMiddleware, configure_logging
from oceanscope_api.core.settings import Settings, get_settings
from oceanscope_api.live_ais.gateway import LiveAisGateway
from oceanscope_api.live_ais.worker import PelyrWorker


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    settings = application.state.settings
    if not isinstance(settings, Settings):
        raise RuntimeError("application settings are unavailable")
    configure_logging(settings.log_level, settings.environment)
    gateway = LiveAisGateway(worker_configured=settings.pelyr_api_key is not None)
    application.state.live_ais_gateway = gateway
    await gateway.start()

    worker_task: asyncio.Task[None] | None = None
    if settings.pelyr_api_key is not None:
        worker = PelyrWorker(
            api_key=settings.pelyr_api_key,
            position_sink=gateway.position_sink,
            status_sink=gateway.status_sink,
            gap_sink=gateway.gap_sink,
        )
        worker_task = asyncio.create_task(worker.run(), name="pelyr-live-ais-worker")
    application.state.live_ais_worker_task = worker_task

    try:
        yield
    finally:
        if worker_task is not None:
            worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await worker_task
        await gateway.stop()


def create_app(*, settings: Settings | None = None) -> FastAPI:
    selected_settings = settings or get_settings()
    application = FastAPI(
        title="OceanScope API",
        summary="Engineering foundation for OceanScope",
        version=__version__,
        lifespan=lifespan,
    )
    application.state.settings = selected_settings
    application.add_middleware(CorrelationIdMiddleware)

    if selected_settings.cors_origin_list:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=selected_settings.cors_origin_list,
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["Content-Type", "X-Correlation-ID"],
        )

    install_exception_handlers(application)
    application.include_router(health_router)
    application.include_router(ports_router)
    application.include_router(earthquakes_router)
    application.include_router(ocean_router)
    application.include_router(data_router)
    application.include_router(system_router)
    application.include_router(live_ais_router)
    return application


app = create_app()
