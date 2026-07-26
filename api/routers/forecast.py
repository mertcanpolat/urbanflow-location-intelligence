from typing import Any

from fastapi import APIRouter, Depends, Query

from api.models.filters import (
    DashboardFilters,
    get_dashboard_filters,
)
from api.models.responses import (
    DailyDemandForecastItem,
)
from api.services.forecast_service import (
    get_daily_demand_forecast as get_daily_demand_forecast_service,
)


router = APIRouter(
    prefix="/api/v1/forecast",
    tags=["Forecast"],
)


@router.get(
    "/daily-demand",
    response_model=list[DailyDemandForecastItem],
)
def get_daily_demand_forecast(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
    forecast_days: int = Query(
        default=7,
        ge=1,
        le=30,
    ),
    history_weeks: int = Query(
        default=4,
        ge=2,
        le=12,
    ),
) -> list[dict[str, Any]]:
    """Return baseline daily demand forecasts."""

    return get_daily_demand_forecast_service(
        filters=filters,
        forecast_days=forecast_days,
        history_weeks=history_weeks,
    )