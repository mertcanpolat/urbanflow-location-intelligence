import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.database import engine
from api.models.responses import HealthResponse


logger = logging.getLogger(
    "urbanflow.system_router"
)


router = APIRouter(
    tags=["System"],
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = PROJECT_ROOT / "web"


@router.get(
    "/map",
    include_in_schema=False,
)
def serve_map() -> FileResponse:
    """Serve the local UrbanFlow web map."""

    logger.info("Map page requested")

    return FileResponse(
        WEB_DIR / "index.html"
    )


@router.get("/")
def root() -> dict[str, str]:
    """Return basic API information."""

    logger.info("Root endpoint requested")

    return {
        "application": "UrbanFlow Location Intelligence API",
        "version": "0.1.0",
        "documentation": "/docs",
    }


@router.get(
    "/health",
    response_model=HealthResponse,
)
def health_check() -> dict[str, str]:
    """Check API and database availability."""

    logger.info("Health check requested")

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SELECT 1")
            )

        logger.info("Health check succeeded")

        return {
            "status": "healthy",
            "database": "connected",
        }

    except SQLAlchemyError as exc:
        logger.exception(
            "Health check failed"
        )

        raise HTTPException(
            status_code=503,
            detail="Veritabanı bağlantısı kurulamadı.",
        ) from exc


@router.get("/api/v1/summary")
def get_summary() -> dict[str, Any]:
    """Return overall Taxi Zone and trip statistics."""

    logger.info(
        "Dataset summary requested"
    )

    query = text(
        """
        SELECT
            (
                SELECT COUNT(*)
                FROM core.trips
            ) AS total_trips,

            (
                SELECT COUNT(*)
                FROM raw.rejected_yellow_trips
            ) AS rejected_trips,

            (
                SELECT COUNT(*)
                FROM core.taxi_zones
            ) AS total_zones,

            (
                SELECT MIN(pickup_datetime)
                FROM core.trips
            ) AS earliest_pickup,

            (
                SELECT MAX(pickup_datetime)
                FROM core.trips
            ) AS latest_pickup,

            (
                SELECT ROUND(
                    AVG(trip_distance),
                    2
                )
                FROM core.trips
            ) AS average_trip_distance,

            (
                SELECT ROUND(
                    AVG(total_amount),
                    2
                )
                FROM core.trips
            ) AS average_total_amount
        """
    )

    try:
        with engine.connect() as connection:
            row = (
                connection.execute(query)
                .mappings()
                .one()
            )

        result = dict(row)

        logger.info(
            (
                "Dataset summary fetched: "
                "total_trips=%s rejected_trips=%s "
                "total_zones=%s"
            ),
            result["total_trips"],
            result["rejected_trips"],
            result["total_zones"],
        )

        return result

    except SQLAlchemyError as exc:
        logger.exception(
            "Dataset summary request failed"
        )

        raise HTTPException(
            status_code=500,
            detail="Özet istatistikler alınamadı.",
        ) from exc
    