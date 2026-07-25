import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from api.models.filters import (
    DashboardFilters,
    get_dashboard_filters,
)
from api.models.responses import (
    DailyTrendItem,
    DashboardSummaryResponse,
)
from api.services.dashboard_service import (
    get_daily_trend as get_daily_trend_service,
    get_dashboard_summary as get_dashboard_summary_service,
)


logger = logging.getLogger(
    "urbanflow.dashboard_router"
)


router = APIRouter(
    prefix="/api/v1/dashboard",
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
)
def get_dashboard_summary(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> dict[str, Any]:
    """Return dashboard KPIs for the selected filters."""

    logger.info(
        "Dashboard summary request received"
    )

    result = get_dashboard_summary_service(filters)

    logger.info(
        "Dashboard summary request completed"
    )

    return result

@router.get(
    "/daily-trend",
    response_model=list[DailyTrendItem],
)
def get_daily_trend(
    filters: DashboardFilters = Depends(
        get_dashboard_filters
    ),
) -> list[dict[str, Any]]:
    """Return daily trip demand for dashboard filters."""

    logger.info(
        "Daily trend request received"
    )

    result = get_daily_trend_service(filters)

    logger.info(
        "Daily trend request completed: row_count=%s",
        len(result),
    )

    return result