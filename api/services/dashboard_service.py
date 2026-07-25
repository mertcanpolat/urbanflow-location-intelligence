import logging
from typing import Any

from api.models.filters import DashboardFilters
from api.repositories.dashboard_repository import (
    fetch_daily_trend,
    fetch_dashboard_summary,
)


logger = logging.getLogger(
    "urbanflow.dashboard_service"
)


def get_dashboard_summary(
    filters: DashboardFilters,
) -> dict[str, Any]:
    """Return dashboard KPI data."""

    logger.info(
        "Preparing dashboard summary"
    )

    result = fetch_dashboard_summary(filters)

    return result


def get_daily_trend(
    filters: DashboardFilters,
) -> list[dict[str, Any]]:
    """Return daily dashboard trend data."""

    logger.info(
        "Preparing daily trend"
    )

    result = fetch_daily_trend(filters)

    return result