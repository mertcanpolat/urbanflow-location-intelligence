from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.routers.dashboard import (
    router as dashboard_router,
)
from api.routers.system import router as system_router
from api.routers.zones import router as zones_router

from api.core.logging_config import configure_logging

configure_logging()


from api.core.exceptions import (
    register_exception_handlers,
)

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

register_exception_handlers(app)

app.include_router(system_router)
app.include_router(dashboard_router)
app.include_router(zones_router)

app.mount(
    "/static",
    StaticFiles(directory=WEB_DIR),
    name="static",
)