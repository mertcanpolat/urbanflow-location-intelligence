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
    fetch_zone_hotspots,
    fetch_zone_scores,
    fetch_zone_details,
    fetch_zone_trend,
    fetch_zone_anomalies,
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

def get_zone_hotspots(
    filters: DashboardFilters,
) -> dict[str, Any]:
    """Return spatial hotspot classifications."""

    logger.info(
        "Preparing zone hotspot analysis"
    )

    return fetch_zone_hotspots(filters)

def get_zone_scores(
    filters: DashboardFilters,
) -> dict[str, Any]:
    """Return weighted zone-priority scores."""

    logger.info(
        "Preparing zone score analysis"
    )

    return fetch_zone_scores(filters)

def get_zone_details(
    location_id: int,
    filters: DashboardFilters,
) -> dict[str, Any] | None:
    """Return detailed analytics for one Taxi Zone."""

    logger.info(
        "Preparing zone details: location_id=%s",
        location_id,
    )

    zone = fetch_zone_by_id(location_id)

    if zone is None:
        logger.warning(
            "Details requested for unknown zone: "
            "location_id=%s",
            location_id,
        )

        return None

    return fetch_zone_details(
        location_id=location_id,
        filters=filters,
    )
    
def get_zone_trend(
    location_id: int,
    filters: DashboardFilters,
    period_days: int,
) -> dict[str, Any] | None:
    """Return period-over-period demand trend for one zone."""

    logger.info(
        "Preparing zone trend: location_id=%s "
        "period_days=%s",
        location_id,
        period_days,
    )

    zone = fetch_zone_by_id(location_id)

    if zone is None:
        logger.warning(
            "Trend requested for unknown zone: "
            "location_id=%s",
            location_id,
        )

        return None

    return fetch_zone_trend(
        location_id=location_id,
        filters=filters,
        period_days=period_days,
    )
    
def get_zone_anomalies(
    location_id: int,
    filters: DashboardFilters,
    analysis_days: int,
    z_threshold: float,
) -> dict[str, Any] | None:
    """Return anomalous daily-demand observations for one zone."""

    logger.info(
        "Preparing zone anomalies: location_id=%s "
        "analysis_days=%s z_threshold=%s",
        location_id,
        analysis_days,
        z_threshold,
    )

    zone = fetch_zone_by_id(location_id)

    if zone is None:
        logger.warning(
            "Anomalies requested for unknown zone: "
            "location_id=%s",
            location_id,
        )

        return None

    return fetch_zone_anomalies(
        location_id=location_id,
        filters=filters,
        analysis_days=analysis_days,
        z_threshold=z_threshold,
    )