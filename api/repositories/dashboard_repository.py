from typing import Any

from sqlalchemy import text

from api.database import engine
from api.models.filters import DashboardFilters, filters_to_dict
import logging

logger = logging.getLogger(
    "urbanflow.dashboard_repository"
)

def fetch_dashboard_summary(
    filters: DashboardFilters,
) -> dict[str, Any]:
    logger.info(
    "Fetching dashboard summary with filters=%s",
    filters_to_dict(filters),
)
    query = text(
        """
        SELECT
            COALESCE(
                SUM(d.trip_count),
                0
            )::bigint AS total_trips,

            COUNT(
                DISTINCT d.location_id
            )::integer AS active_zones,

            ROUND(
                (
                    SUM(d.total_amount)
                    / NULLIF(SUM(d.trip_count), 0)
                )::numeric,
                2
            ) AS avg_total_amount,

            ROUND(
                (
                    SUM(
                        d.avg_trip_distance
                        * d.trip_count
                    )
                    / NULLIF(SUM(d.trip_count), 0)
                )::numeric,
                2
            ) AS avg_trip_distance

        FROM analytics.zone_hourly_demand AS d

        JOIN core.taxi_zones AS z
            ON d.location_id = z.location_id

        WHERE (
            CAST(:borough AS VARCHAR) IS NULL
            OR z.borough = CAST(:borough AS VARCHAR)
        )
        AND (
            CAST(:hour AS SMALLINT) IS NULL
            OR d.pickup_hour = CAST(:hour AS SMALLINT)
        )
        AND (
            CAST(:weekday AS SMALLINT) IS NULL
            OR EXTRACT(ISODOW FROM d.pickup_date)
                = CAST(:weekday AS SMALLINT)
        )
        AND (
            CAST(:date_from AS DATE) IS NULL
            OR d.pickup_date >= CAST(:date_from AS DATE)
        )
        AND (
            CAST(:date_to AS DATE) IS NULL
            OR d.pickup_date <= CAST(:date_to AS DATE)
        )
        """
    )

    parameters = filters_to_dict(filters)

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                parameters,
            )
            .mappings()
            .one()
        )

    result = dict(row)

    logger.info(
        "Dashboard summary fetched: total_trips=%s active_zones=%s",
        result["total_trips"],
        result["active_zones"],
    )

    return result


def fetch_daily_trend(
    filters: DashboardFilters,
) -> list[dict[str, Any]]:
    logger.info(
    "Fetching daily trend with filters=%s",
    filters_to_dict(filters),
)
    query = text(
        """
        SELECT
            d.pickup_date,
            SUM(d.trip_count)::bigint AS trip_count,

            ROUND(
                (
                    SUM(d.total_amount)
                    / NULLIF(SUM(d.trip_count), 0)
                )::numeric,
                2
            ) AS avg_total_amount

        FROM analytics.zone_hourly_demand AS d

        JOIN core.taxi_zones AS z
            ON d.location_id = z.location_id

        WHERE (
            CAST(:borough AS VARCHAR) IS NULL
            OR z.borough = CAST(:borough AS VARCHAR)
        )
        AND (
            CAST(:hour AS SMALLINT) IS NULL
            OR d.pickup_hour = CAST(:hour AS SMALLINT)
        )
        AND (
            CAST(:weekday AS SMALLINT) IS NULL
            OR EXTRACT(ISODOW FROM d.pickup_date)
                = CAST(:weekday AS SMALLINT)
        )
        AND (
            CAST(:date_from AS DATE) IS NULL
            OR d.pickup_date >= CAST(:date_from AS DATE)
        )
        AND (
            CAST(:date_to AS DATE) IS NULL
            OR d.pickup_date <= CAST(:date_to AS DATE)
        )

        GROUP BY d.pickup_date
        ORDER BY d.pickup_date
        """
    )

    parameters = filters_to_dict(filters)

    with engine.connect() as connection:
        rows = (
            connection.execute(
                query,
                parameters,
            )
            .mappings()
            .all()
        )

    result = [dict(row) for row in rows]

    logger.info(
        "Daily trend fetched: row_count=%s",
        len(result),
    )

    return result