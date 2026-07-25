from datetime import date
from typing import Any

from fastapi import HTTPException, Query
from pydantic import BaseModel


class DashboardFilters(BaseModel):
    borough: str | None = None
    hour: int | None = None
    weekday: int | None = None
    date_from: date | None = None
    date_to: date | None = None


def get_dashboard_filters(
    borough: str | None = Query(default=None),
    hour: int | None = Query(default=None),
    weekday: int | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
) -> DashboardFilters:
    if hour is not None and not 0 <= hour <= 23:
        raise HTTPException(
            status_code=422,
            detail="Hour must be between 0 and 23.",
        )

    if weekday is not None and not 1 <= weekday <= 7:
        raise HTTPException(
            status_code=422,
            detail="Weekday must be between 1 and 7.",
        )

    if (
        date_from is not None
        and date_to is not None
        and date_from > date_to
    ):
        raise HTTPException(
            status_code=400,
            detail="Start date cannot be later than end date.",
        )

    return DashboardFilters(
        borough=borough,
        hour=hour,
        weekday=weekday,
        date_from=date_from,
        date_to=date_to,
    )


def filters_to_dict(
    filters: DashboardFilters,
) -> dict[str, Any]:
    if hasattr(filters, "model_dump"):
        return filters.model_dump()

    return filters.dict()