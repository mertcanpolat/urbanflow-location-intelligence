import logging
from typing import Any

from api.models.filters import DashboardFilters
from api.repositories.zone_repository import (
    fetch_boroughs,
    fetch_top_zones,
    fetch_zone_by_id,
    fetch_zone_hourly_demand,
    fetch_zone_ranking,
    fetch_zones_geojson,
)


logger = logging.getLogger(
    "urbanflow.zone_service"
)


def get_boroughs() -> list[str]:
    """Return available borough names."""

    logger.info("Preparing borough list")

    return fetch_boroughs()


def get_top_zones(
    limit: int,
) -> list[dict[str, Any]]:
    """Return zones with the highest overall demand."""

    logger.info(
        "Preparing top zones: limit=%s",
        limit,
    )

    return fetch_top_zones(limit)


def get_zones_geojson(
    filters: DashboardFilters,
) -> dict[str, Any]:
    """Return filtered Taxi Zones as GeoJSON."""

    logger.info(
        "Preparing zones GeoJSON"
    )

    return fetch_zones_geojson(filters)


def get_zone_ranking(
    filters: DashboardFilters,
    limit: int,
) -> list[dict[str, Any]]:
    """Return filtered zone ranking."""

    logger.info(
        "Preparing zone ranking: limit=%s",
        limit,
    )

    return fetch_zone_ranking(
        filters=filters,
        limit=limit,
    )


def get_zone_hourly_demand(
    location_id: int,
    filters: DashboardFilters,
) -> list[dict[str, Any]] | None:
    """Return hourly demand or None when zone does not exist."""

    logger.info(
        "Preparing hourly demand: location_id=%s",
        location_id,
    )

    zone = fetch_zone_by_id(location_id)

    if zone is None:
        logger.warning(
            "Hourly demand requested for unknown zone: "
            "location_id=%s",
            location_id,
        )

        return None

    return fetch_zone_hourly_demand(
        location_id=location_id,
        filters=filters,
    )