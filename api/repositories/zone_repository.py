import logging
from typing import Any

from sqlalchemy import text

from api.database import engine
from api.models.filters import DashboardFilters, filters_to_dict


logger = logging.getLogger(
    "urbanflow.zone_repository"
)


def fetch_boroughs() -> list[str]:
    logger.info("Fetching borough list")

    query = text(
        """
        SELECT DISTINCT borough
        FROM core.taxi_zones
        WHERE borough IS NOT NULL
        ORDER BY borough
        """
    )

    with engine.connect() as connection:
        rows = connection.execute(query).scalars().all()

    result = list(rows)

    logger.info(
        "Borough list fetched: count=%s",
        len(result),
    )

    return result


def fetch_top_zones(
    limit: int,
) -> list[dict[str, Any]]:
    logger.info(
        "Fetching top zones: limit=%s",
        limit,
    )

    query = text(
        """
        SELECT
            z.location_id,
            z.zone_name,
            z.borough,
            COUNT(*) AS trip_count,
            ROUND(
                AVG(t.trip_distance),
                2
            ) AS avg_trip_distance,
            ROUND(
                AVG(t.total_amount),
                2
            ) AS avg_total_amount

        FROM core.trips AS t

        JOIN core.taxi_zones AS z
            ON t.pickup_location_id = z.location_id

        GROUP BY
            z.location_id,
            z.zone_name,
            z.borough

        ORDER BY trip_count DESC

        LIMIT :limit
        """
    )

    with engine.connect() as connection:
        rows = (
            connection.execute(
                query,
                {"limit": limit},
            )
            .mappings()
            .all()
        )

    result = [dict(row) for row in rows]

    logger.info(
        "Top zones fetched: row_count=%s",
        len(result),
    )

    return result


def fetch_zones_geojson(
    filters: DashboardFilters,
) -> dict[str, Any]:
    parameters = filters_to_dict(filters)

    logger.info(
        "Fetching GeoJSON with filters=%s",
        parameters,
    )

    query = text(
        """
        WITH demand AS (
            SELECT
                location_id,
                SUM(trip_count)::bigint AS trip_count,

                ROUND(
                    (
                        SUM(total_amount)
                        / NULLIF(SUM(trip_count), 0)
                    )::numeric,
                    2
                ) AS avg_total_amount,

                ROUND(
                    (
                        SUM(
                            avg_trip_distance
                            * trip_count
                        )
                        / NULLIF(SUM(trip_count), 0)
                    )::numeric,
                    2
                ) AS avg_trip_distance

            FROM analytics.zone_hourly_demand

            WHERE (
                CAST(:hour AS SMALLINT) IS NULL
                OR pickup_hour = CAST(:hour AS SMALLINT)
            )
            AND (
                CAST(:weekday AS SMALLINT) IS NULL
                OR EXTRACT(ISODOW FROM pickup_date)
                    = CAST(:weekday AS SMALLINT)
            )
            AND (
                CAST(:date_from AS DATE) IS NULL
                OR pickup_date >= CAST(:date_from AS DATE)
            )
            AND (
                CAST(:date_to AS DATE) IS NULL
                OR pickup_date <= CAST(:date_to AS DATE)
            )

            GROUP BY location_id
        )

        SELECT
            z.location_id,
            z.zone_name,
            z.borough,
            COALESCE(
                d.trip_count,
                0
            )::bigint AS trip_count,
            d.avg_total_amount,
            d.avg_trip_distance,
            ST_AsGeoJSON(
                z.geom,
                6
            )::json AS geometry

        FROM core.taxi_zones AS z

        LEFT JOIN demand AS d
            ON z.location_id = d.location_id

        WHERE (
            CAST(:borough AS VARCHAR) IS NULL
            OR z.borough = CAST(:borough AS VARCHAR)
        )

        ORDER BY z.location_id
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

    features = [
        {
            "type": "Feature",
            "geometry": row["geometry"],
            "properties": {
                "location_id": row["location_id"],
                "zone_name": row["zone_name"],
                "borough": row["borough"],
                "trip_count": row["trip_count"],
                "avg_total_amount": row["avg_total_amount"],
                "avg_trip_distance": row["avg_trip_distance"],
            },
        }
        for row in rows
    ]

    logger.info(
        "GeoJSON generated: feature_count=%s",
        len(features),
    )

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def fetch_zone_ranking(
    filters: DashboardFilters,
    limit: int,
) -> list[dict[str, Any]]:
    parameters = {
        **filters_to_dict(filters),
        "limit": limit,
    }

    logger.info(
        "Fetching zone ranking: filters=%s limit=%s",
        filters_to_dict(filters),
        limit,
    )

    query = text(
        """
        SELECT
            d.location_id,
            z.zone_name,
            z.borough,
            SUM(d.trip_count)::bigint AS trip_count,

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

        GROUP BY
            d.location_id,
            z.zone_name,
            z.borough

        ORDER BY trip_count DESC

        LIMIT :limit
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
        "Zone ranking fetched: row_count=%s",
        len(result),
    )

    return result


def fetch_zone_by_id(
    location_id: int,
) -> dict[str, Any] | None:
    logger.info(
        "Fetching zone by id: location_id=%s",
        location_id,
    )

    query = text(
        """
        SELECT
            location_id,
            zone_name,
            borough

        FROM core.taxi_zones

        WHERE location_id = :location_id
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                {"location_id": location_id},
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        logger.warning(
            "Zone not found: location_id=%s",
            location_id,
        )

        return None

    result = dict(row)

    logger.info(
        "Zone fetched: location_id=%s zone_name=%s",
        result["location_id"],
        result["zone_name"],
    )

    return result


def fetch_zone_hourly_demand(
    location_id: int,
    filters: DashboardFilters,
) -> list[dict[str, Any]]:
    parameters = filters_to_dict(filters)

    parameters.pop("hour", None)
    parameters["location_id"] = location_id

    logger.info(
        "Fetching hourly demand: location_id=%s filters=%s",
        location_id,
        filters_to_dict(filters),
    )

    query = text(
        """
        SELECT
            pickup_hour,
            SUM(trip_count)::bigint AS trip_count,

            ROUND(
                (
                    SUM(total_amount)
                    / NULLIF(SUM(trip_count), 0)
                )::numeric,
                2
            ) AS avg_total_amount

        FROM analytics.zone_hourly_demand

        WHERE location_id = :location_id

        AND (
            CAST(:weekday AS SMALLINT) IS NULL
            OR EXTRACT(ISODOW FROM pickup_date)
                = CAST(:weekday AS SMALLINT)
        )

        AND (
            CAST(:date_from AS DATE) IS NULL
            OR pickup_date >= CAST(:date_from AS DATE)
        )

        AND (
            CAST(:date_to AS DATE) IS NULL
            OR pickup_date <= CAST(:date_to AS DATE)
        )

        GROUP BY pickup_hour
        ORDER BY pickup_hour
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
        "Hourly demand fetched: location_id=%s row_count=%s",
        location_id,
        len(result),
    )

    return result