import logging
from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from api.core.exceptions import register_exception_handlers
from api.core.logging_config import configure_logging
from api.routers.dashboard import router as dashboard_router
from api.routers.system import router as system_router
from api.routers.zones import router as zones_router
from api.routers.forecast import router as forecast_router


configure_logging()

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"


app = FastAPI(
    title="UrbanFlow Location Intelligence API",
    description=(
        "NYC Yellow Taxi verilerini PostGIS üzerinden "
        "sunan Location Intelligence API'si."
    ),
    version="0.1.0",
)


@app.middleware("http")
async def log_request_duration(
    request: Request,
    call_next,
):
    """
    Her HTTP isteğinin toplam işlem süresini ölçer ve loglar.
    """

    start_time = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (perf_counter() - start_time) * 1000

        logger.exception(
            "%s %s - ERROR - %.2f ms",
            request.method,
            request.url.path,
            duration_ms,
        )

        raise

    duration_ms = (perf_counter() - start_time) * 1000

    response.headers["X-Process-Time-Ms"] = (
        f"{duration_ms:.2f}"
    )

    logger.info(
        "%s %s - %s - %.2f ms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )

    return response


register_exception_handlers(app)

app.include_router(system_router)
app.include_router(dashboard_router)
app.include_router(zones_router)
app.include_router(forecast_router)

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static",
)