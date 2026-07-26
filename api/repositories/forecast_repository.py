import logging
from typing import Any

from sqlalchemy import text

from api.database import engine
from api.models.filters import DashboardFilters, filters_to_dict


logger = logging.getLogger(
    "urbanflow.forecast_repository"
)


def fetch_daily_demand_forecast(
    filters: DashboardFilters,
    forecast_days: int = 7,
    history_weeks: int = 4,
) -> list[dict[str, Any]]:
    parameters = {
        **filters_to_dict(filters),
        "forecast_days": forecast_days,
        "history_weeks": history_weeks,
    }

    parameters.pop("hour", None)
    parameters.pop("weekday", None)
    parameters.pop("date_from", None)
    parameters.pop("date_to", None)

    logger.info(
        "Fetching daily demand forecast: "
        "filters=%s forecast_days=%s history_weeks=%s",
        filters_to_dict(filters),
        forecast_days,
        history_weeks,
    )

    query = text(
        """
        WITH daily_demand AS (
            SELECT
                d.pickup_date,
                SUM(d.trip_count)::bigint AS trip_count

            FROM analytics.zone_hourly_demand AS d

            JOIN core.taxi_zones AS z
                ON d.location_id = z.location_id

            WHERE (
                CAST(:borough AS VARCHAR) IS NULL
                OR z.borough = CAST(:borough AS VARCHAR)
            )

            GROUP BY d.pickup_date
        ),

        dataset_limits AS (
            SELECT
                MAX(pickup_date) AS max_date
            FROM daily_demand
        ),

        forecast_dates AS (
            SELECT
                (
                    limits.max_date
                    + generated.day_offset
                )::date AS forecast_date

            FROM dataset_limits AS limits

            CROSS JOIN generate_series(
                1,
                CAST(:forecast_days AS INTEGER)
            ) AS generated(day_offset)
        ),

        historical_candidates AS (
            SELECT
                f.forecast_date,
                d.pickup_date,
                d.trip_count,

                ROW_NUMBER() OVER (
                    PARTITION BY f.forecast_date
                    ORDER BY d.pickup_date DESC
                ) AS history_rank

            FROM forecast_dates AS f

            JOIN daily_demand AS d
                ON EXTRACT(
                    ISODOW FROM d.pickup_date
                ) = EXTRACT(
                    ISODOW FROM f.forecast_date
                )
                AND d.pickup_date < f.forecast_date
        ),

        historical_samples AS (
            SELECT
                forecast_date,
                trip_count

            FROM historical_candidates

            WHERE history_rank
                <= CAST(:history_weeks AS INTEGER)
        )

        SELECT
            forecast_date,

            EXTRACT(
                ISODOW FROM forecast_date
            )::smallint AS weekday,

            ROUND(
                AVG(trip_count)
            )::bigint AS predicted_trip_count,

            GREATEST(
                ROUND(
                    AVG(trip_count)
                    - COALESCE(
                        STDDEV_POP(trip_count),
                        0
                    )
                ),
                0
            )::bigint AS lower_bound,

            ROUND(
                AVG(trip_count)
                + COALESCE(
                    STDDEV_POP(trip_count),
                    0
                )
            )::bigint AS upper_bound,

            COUNT(*)::integer AS sample_count

        FROM historical_samples

        GROUP BY forecast_date

        ORDER BY forecast_date
        """
    )

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
        "Daily demand forecast fetched: row_count=%s",
        len(result),
    )

    return result