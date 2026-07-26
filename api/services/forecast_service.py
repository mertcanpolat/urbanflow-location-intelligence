import logging
from typing import Any

from api.models.filters import DashboardFilters
from api.repositories.forecast_repository import (
    fetch_daily_demand_forecast,
)


logger = logging.getLogger(
    "urbanflow.forecast_service"
)


def get_daily_demand_forecast(
    filters: DashboardFilters,
    forecast_days: int,
    history_weeks: int,
) -> list[dict[str, Any]]:
    """Return baseline daily demand forecasts."""

    logger.info(
        "Preparing daily demand forecast"
    )

    return fetch_daily_demand_forecast(
        filters=filters,
        forecast_days=forecast_days,
        history_weeks=history_weeks,
    )