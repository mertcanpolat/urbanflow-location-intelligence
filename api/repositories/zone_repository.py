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
                d.location_id,

                SUM(
                    d.trip_count
                )::bigint AS trip_count,

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

            GROUP BY d.location_id
        ),

        classified_demand AS (
            SELECT
                location_id,
                trip_count,
                avg_total_amount,
                avg_trip_distance,

                CUME_DIST() OVER (
                    ORDER BY trip_count
                ) AS demand_percentile

            FROM demand

            WHERE trip_count > 0
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

            CASE
                WHEN d.location_id IS NULL THEN 0
                WHEN d.demand_percentile <= 0.20 THEN 1
                WHEN d.demand_percentile <= 0.40 THEN 2
                WHEN d.demand_percentile <= 0.60 THEN 3
                WHEN d.demand_percentile <= 0.80 THEN 4
                ELSE 5
            END::smallint AS demand_class_id,

            CASE
                WHEN d.location_id IS NULL THEN 'Veri Yok'
                WHEN d.demand_percentile <= 0.20 THEN 'Çok Düşük'
                WHEN d.demand_percentile <= 0.40 THEN 'Düşük'
                WHEN d.demand_percentile <= 0.60 THEN 'Orta'
                WHEN d.demand_percentile <= 0.80 THEN 'Yüksek'
                ELSE 'Çok Yüksek'
            END AS demand_class,

            ST_AsGeoJSON(
                ST_SimplifyPreserveTopology(
                    z.geom,
                    0.0001
                ),
                6
            )::json AS geometry

        FROM core.taxi_zones AS z

        LEFT JOIN classified_demand AS d
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
                "demand_class_id": row["demand_class_id"],
                "demand_class": row["demand_class"],
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

            SUM(
                d.trip_count
            )::bigint AS trip_count,

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

            SUM(
                trip_count
            )::bigint AS trip_count,

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


def fetch_zone_hotspots(
    filters: DashboardFilters,
) -> dict[str, Any]:
    parameters = filters_to_dict(filters)

    logger.info(
        "Fetching zone hotspots with filters=%s",
        parameters,
    )

    query = text(
        """
        WITH filtered_demand AS (
            SELECT
                d.location_id,

                SUM(
                    d.trip_count
                )::bigint AS trip_count

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

            GROUP BY d.location_id
        ),

        selected_zones AS (
            SELECT
                z.location_id,
                z.zone_name,
                z.borough,
                z.geom,

                COALESCE(
                    d.trip_count,
                    0
                )::bigint AS trip_count

            FROM core.taxi_zones AS z

            LEFT JOIN filtered_demand AS d
                ON z.location_id = d.location_id

            WHERE (
                CAST(:borough AS VARCHAR) IS NULL
                OR z.borough = CAST(:borough AS VARCHAR)
            )
        ),

        neighbours AS (
            SELECT
                a.location_id,

                COUNT(
                    b.location_id
                )::integer AS neighbour_count,

                COALESCE(
                    AVG(
                        b.trip_count
                    ),
                    0
                )::numeric AS neighbour_avg_trip_count

            FROM selected_zones AS a

            LEFT JOIN selected_zones AS b
                ON a.location_id <> b.location_id
                AND ST_Touches(
                    a.geom,
                    b.geom
                )

            GROUP BY a.location_id
        ),

        scored AS (
            SELECT
                z.location_id,
                z.zone_name,
                z.borough,
                z.geom,
                z.trip_count,

                COALESCE(
                    n.neighbour_count,
                    0
                ) AS neighbour_count,

                ROUND(
                    COALESCE(
                        n.neighbour_avg_trip_count,
                        0
                    ),
                    2
                ) AS neighbour_avg_trip_count

            FROM selected_zones AS z

            LEFT JOIN neighbours AS n
                ON z.location_id = n.location_id
        ),

        percentiles AS (
            SELECT
                location_id,
                zone_name,
                borough,
                geom,
                trip_count,
                neighbour_count,
                neighbour_avg_trip_count,

                CUME_DIST() OVER (
                    ORDER BY trip_count
                ) AS zone_percentile,

                CUME_DIST() OVER (
                    ORDER BY neighbour_avg_trip_count
                ) AS neighbour_percentile

            FROM scored
        )

        SELECT
            location_id,
            zone_name,
            borough,
            trip_count,
            neighbour_count,
            neighbour_avg_trip_count,

            CASE
                WHEN neighbour_count = 0 THEN 0

                WHEN zone_percentile >= 0.80
                AND neighbour_percentile >= 0.80
                    THEN 2

                WHEN zone_percentile >= 0.60
                AND neighbour_percentile >= 0.60
                    THEN 1

                WHEN zone_percentile <= 0.20
                AND neighbour_percentile <= 0.20
                    THEN -2

                WHEN zone_percentile <= 0.40
                AND neighbour_percentile <= 0.40
                    THEN -1

                ELSE 0
            END::smallint AS hotspot_score,

            CASE
                WHEN neighbour_count = 0
                    THEN 'Nötr'

                WHEN zone_percentile >= 0.80
                AND neighbour_percentile >= 0.80
                    THEN 'Hotspot'

                WHEN zone_percentile >= 0.60
                AND neighbour_percentile >= 0.60
                    THEN 'Potansiyel Hotspot'

                WHEN zone_percentile <= 0.20
                AND neighbour_percentile <= 0.20
                    THEN 'Coldspot'

                WHEN zone_percentile <= 0.40
                AND neighbour_percentile <= 0.40
                    THEN 'Potansiyel Coldspot'

                ELSE 'Nötr'
            END AS hotspot_class,

            ST_AsGeoJSON(
                ST_SimplifyPreserveTopology(
                    geom,
                    0.0001
                ),
                6
            )::json AS geometry

        FROM percentiles

        ORDER BY location_id
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
                "neighbour_count": row["neighbour_count"],
                "neighbour_avg_trip_count": float(
                    row["neighbour_avg_trip_count"]
                ),
                "hotspot_score": row["hotspot_score"],
                "hotspot_class": row["hotspot_class"],
            },
        }
        for row in rows
    ]

    logger.info(
        "Zone hotspots generated: feature_count=%s",
        len(features),
    )

    return {
        "type": "FeatureCollection",
        "features": features,
    }

def fetch_zone_scores(
    filters: DashboardFilters,
) -> dict[str, Any]:
    parameters = filters_to_dict(filters)

    logger.info(
        "Fetching zone scores with filters=%s",
        parameters,
    )

    query = text(
        """
        WITH filtered_daily_demand AS (
            SELECT
                d.location_id,
                d.pickup_date,

                SUM(
                    d.trip_count
                )::bigint AS trip_count

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
                OR EXTRACT(
                    ISODOW FROM d.pickup_date
                ) = CAST(:weekday AS SMALLINT)
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
                d.pickup_date
        ),

        period_statistics AS (
            SELECT
                COUNT(
                    DISTINCT pickup_date
                )::integer AS total_day_count

            FROM filtered_daily_demand
        ),

        demand_by_zone AS (
            SELECT
                location_id,

                SUM(
                    trip_count
                )::bigint AS trip_count,

                COUNT(
                    DISTINCT pickup_date
                )::integer AS active_day_count

            FROM filtered_daily_demand

            GROUP BY location_id
        ),

        selected_zones AS (
            SELECT
                z.location_id,
                z.zone_name,
                z.borough,
                z.geom,

                COALESCE(
                    d.trip_count,
                    0
                )::bigint AS trip_count,

                COALESCE(
                    d.active_day_count,
                    0
                )::integer AS active_day_count,

                COALESCE(
                    p.total_day_count,
                    0
                )::integer AS total_day_count

            FROM core.taxi_zones AS z

            LEFT JOIN demand_by_zone AS d
                ON z.location_id = d.location_id

            CROSS JOIN period_statistics AS p

            WHERE (
                CAST(:borough AS VARCHAR) IS NULL
                OR z.borough = CAST(:borough AS VARCHAR)
            )
        ),

        neighbours AS (
            SELECT
                a.location_id,

                COUNT(
                    b.location_id
                )::integer AS neighbour_count,

                COALESCE(
                    AVG(
                        b.trip_count
                    ),
                    0
                )::numeric AS neighbour_avg_trip_count

            FROM selected_zones AS a

            LEFT JOIN selected_zones AS b
                ON a.location_id <> b.location_id
                AND ST_Touches(
                    a.geom,
                    b.geom
                )

            GROUP BY a.location_id
        ),

        spatial_metrics AS (
            SELECT
                z.location_id,
                z.zone_name,
                z.borough,
                z.geom,
                z.trip_count,
                z.active_day_count,
                z.total_day_count,

                COALESCE(
                    n.neighbour_count,
                    0
                )::integer AS neighbour_count,

                COALESCE(
                    n.neighbour_avg_trip_count,
                    0
                )::numeric AS neighbour_avg_trip_count

            FROM selected_zones AS z

            LEFT JOIN neighbours AS n
                ON z.location_id = n.location_id
        ),

        positive_demand_percentiles AS (
            SELECT
                location_id,

                CUME_DIST() OVER (
                    ORDER BY trip_count
                ) AS demand_percentile

            FROM spatial_metrics

            WHERE trip_count > 0
        ),

        spatial_percentiles AS (
            SELECT
                location_id,

                CUME_DIST() OVER (
                    ORDER BY neighbour_avg_trip_count
                ) AS neighbour_percentile

            FROM spatial_metrics
        ),

        component_scores AS (
            SELECT
                m.location_id,
                m.zone_name,
                m.borough,
                m.geom,
                m.trip_count,
                m.active_day_count,
                m.total_day_count,
                m.neighbour_count,

                ROUND(
                    (
                        COALESCE(
                            d.demand_percentile,
                            0
                        ) * 100
                    )::numeric,
                    2
                ) AS demand_score,

                CASE
                    WHEN m.neighbour_count = 0
                        THEN 50

                    WHEN d.demand_percentile >= 0.80
                    AND s.neighbour_percentile >= 0.80
                        THEN 100

                    WHEN d.demand_percentile >= 0.60
                    AND s.neighbour_percentile >= 0.60
                        THEN 75

                    WHEN d.demand_percentile <= 0.20
                    AND s.neighbour_percentile <= 0.20
                        THEN 0

                    WHEN d.demand_percentile <= 0.40
                    AND s.neighbour_percentile <= 0.40
                        THEN 25

                    ELSE 50
                END::numeric AS hotspot_component_score,

                ROUND(
                    (
                        100.0
                        * m.active_day_count
                        / NULLIF(
                            m.total_day_count,
                            0
                        )
                    )::numeric,
                    2
                ) AS consistency_score

            FROM spatial_metrics AS m

            LEFT JOIN positive_demand_percentiles AS d
                ON m.location_id = d.location_id

            LEFT JOIN spatial_percentiles AS s
                ON m.location_id = s.location_id
        ),

        final_scores AS (
            SELECT
                location_id,
                zone_name,
                borough,
                geom,
                trip_count,
                active_day_count,
                total_day_count,
                demand_score,
                hotspot_component_score,

                COALESCE(
                    consistency_score,
                    0
                )::numeric AS consistency_score,

                ROUND(
                    (
                        demand_score * 0.50
                        + hotspot_component_score * 0.30
                        + COALESCE(
                            consistency_score,
                            0
                        ) * 0.20
                    )::numeric,
                    2
                ) AS zone_score

            FROM component_scores
        )

        SELECT
            location_id,
            zone_name,
            borough,
            trip_count,
            active_day_count,
            total_day_count,
            demand_score,
            hotspot_component_score,
            consistency_score,
            zone_score,

            CASE
                WHEN zone_score >= 80
                    THEN 'Çok Yüksek'

                WHEN zone_score >= 60
                    THEN 'Yüksek'

                WHEN zone_score >= 40
                    THEN 'Orta'

                WHEN zone_score >= 20
                    THEN 'Düşük'

                ELSE 'Çok Düşük'
            END AS priority_class,

            ST_AsGeoJSON(
                ST_SimplifyPreserveTopology(
                    geom,
                    0.0001
                ),
                6
            )::json AS geometry

        FROM final_scores

        ORDER BY
            zone_score DESC,
            location_id
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
                "active_day_count": row["active_day_count"],
                "total_day_count": row["total_day_count"],
                "demand_score": float(
                    row["demand_score"]
                ),
                "hotspot_component_score": float(
                    row["hotspot_component_score"]
                ),
                "consistency_score": float(
                    row["consistency_score"]
                ),
                "zone_score": float(
                    row["zone_score"]
                ),
                "priority_class": row["priority_class"],
            },
        }
        for row in rows
    ]

    logger.info(
        "Zone scores generated: feature_count=%s",
        len(features),
    )

    return {
        "type": "FeatureCollection",
        "features": features,
    }