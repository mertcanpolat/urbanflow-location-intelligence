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
    
def fetch_zone_details(
    location_id: int,
    filters: DashboardFilters,
) -> dict[str, Any] | None:
    parameters = {
        **filters_to_dict(filters),
        "location_id": location_id,
    }

    logger.info(
        "Fetching zone details: location_id=%s filters=%s",
        location_id,
        filters_to_dict(filters),
    )

    query = text(
        """
        WITH filtered_hourly_demand AS (
            SELECT
                d.location_id,
                d.pickup_date,
                d.pickup_hour,

                SUM(
                    d.trip_count
                )::bigint AS trip_count,

                SUM(
                    d.total_amount
                )::numeric AS total_amount,

                SUM(
                    d.avg_trip_distance
                    * d.trip_count
                )::numeric AS weighted_trip_distance

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
                d.pickup_date,
                d.pickup_hour
        ),

        period_statistics AS (
            SELECT
                COUNT(
                    DISTINCT pickup_date
                )::integer AS total_day_count

            FROM filtered_hourly_demand
        ),

        zone_metrics AS (
            SELECT
                location_id,

                SUM(
                    trip_count
                )::bigint AS trip_count,

                ROUND(
                    (
                        SUM(total_amount)
                        / NULLIF(
                            SUM(trip_count),
                            0
                        )
                    )::numeric,
                    2
                ) AS avg_total_amount,

                ROUND(
                    (
                        SUM(weighted_trip_distance)
                        / NULLIF(
                            SUM(trip_count),
                            0
                        )
                    )::numeric,
                    2
                ) AS avg_trip_distance,

                COUNT(
                    DISTINCT pickup_date
                )::integer AS active_day_count

            FROM filtered_hourly_demand

            GROUP BY location_id
        ),

        selected_zones AS (
            SELECT
                z.location_id,
                z.zone_name,
                z.borough,
                z.geom,

                COALESCE(
                    m.trip_count,
                    0
                )::bigint AS trip_count,

                m.avg_total_amount,
                m.avg_trip_distance,

                COALESCE(
                    m.active_day_count,
                    0
                )::integer AS active_day_count,

                COALESCE(
                    p.total_day_count,
                    0
                )::integer AS total_day_count

            FROM core.taxi_zones AS z

            LEFT JOIN zone_metrics AS m
                ON z.location_id = m.location_id

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
                z.avg_total_amount,
                z.avg_trip_distance,
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

        neighbour_percentiles AS (
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
                m.trip_count,
                m.avg_total_amount,
                m.avg_trip_distance,
                m.active_day_count,
                m.total_day_count,
                m.neighbour_count,

                COALESCE(
                    d.demand_percentile,
                    0
                ) AS demand_percentile,

                COALESCE(
                    n.neighbour_percentile,
                    0
                ) AS neighbour_percentile,

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
                    AND n.neighbour_percentile >= 0.80
                        THEN 100

                    WHEN d.demand_percentile >= 0.60
                    AND n.neighbour_percentile >= 0.60
                        THEN 75

                    WHEN d.demand_percentile <= 0.20
                    AND n.neighbour_percentile <= 0.20
                        THEN 0

                    WHEN d.demand_percentile <= 0.40
                    AND n.neighbour_percentile <= 0.40
                        THEN 25

                    ELSE 50
                END::numeric AS hotspot_component_score,

                CASE
                    WHEN m.neighbour_count = 0
                        THEN 'Nötr'

                    WHEN d.demand_percentile >= 0.80
                    AND n.neighbour_percentile >= 0.80
                        THEN 'Hotspot'

                    WHEN d.demand_percentile >= 0.60
                    AND n.neighbour_percentile >= 0.60
                        THEN 'Potansiyel Hotspot'

                    WHEN d.demand_percentile <= 0.20
                    AND n.neighbour_percentile <= 0.20
                        THEN 'Coldspot'

                    WHEN d.demand_percentile <= 0.40
                    AND n.neighbour_percentile <= 0.40
                        THEN 'Potansiyel Coldspot'

                    ELSE 'Nötr'
                END AS hotspot_class,

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

            LEFT JOIN neighbour_percentiles AS n
                ON m.location_id = n.location_id
        ),

        final_scores AS (
            SELECT
                location_id,
                zone_name,
                borough,
                trip_count,
                avg_total_amount,
                avg_trip_distance,
                active_day_count,
                total_day_count,
                demand_score,
                hotspot_component_score,
                hotspot_class,

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
        ),

        hourly_ranking AS (
            SELECT
                pickup_hour,

                SUM(
                    trip_count
                )::bigint AS trip_count,

                ROW_NUMBER() OVER (
                    ORDER BY
                        SUM(trip_count) DESC,
                        pickup_hour
                ) AS ranking

            FROM filtered_hourly_demand

            WHERE location_id = :location_id

            GROUP BY pickup_hour
        ),

        weekday_ranking AS (
            SELECT
                EXTRACT(
                    ISODOW FROM pickup_date
                )::integer AS weekday,

                SUM(
                    trip_count
                )::bigint AS trip_count,

                ROW_NUMBER() OVER (
                    ORDER BY
                        SUM(trip_count) DESC,
                        EXTRACT(
                            ISODOW FROM pickup_date
                        )
                ) AS ranking

            FROM filtered_hourly_demand

            WHERE location_id = :location_id

            GROUP BY
                EXTRACT(
                    ISODOW FROM pickup_date
                )
        )

        SELECT
            s.location_id,
            s.zone_name,
            s.borough,
            s.trip_count,
            s.avg_total_amount,
            s.avg_trip_distance,
            s.active_day_count,
            s.total_day_count,

            w.weekday AS peak_weekday,

            CASE w.weekday
                WHEN 1 THEN 'Pazartesi'
                WHEN 2 THEN 'Salı'
                WHEN 3 THEN 'Çarşamba'
                WHEN 4 THEN 'Perşembe'
                WHEN 5 THEN 'Cuma'
                WHEN 6 THEN 'Cumartesi'
                WHEN 7 THEN 'Pazar'
                ELSE NULL
            END AS peak_weekday_name,

            h.pickup_hour AS peak_hour,

            s.demand_score,
            s.hotspot_component_score,
            s.consistency_score,
            s.zone_score,
            s.hotspot_class,

            CASE
                WHEN s.zone_score >= 80
                    THEN 'Çok Yüksek'

                WHEN s.zone_score >= 60
                    THEN 'Yüksek'

                WHEN s.zone_score >= 40
                    THEN 'Orta'

                WHEN s.zone_score >= 20
                    THEN 'Düşük'

                ELSE 'Çok Düşük'
            END AS priority_class

        FROM final_scores AS s

        LEFT JOIN hourly_ranking AS h
            ON h.ranking = 1

        LEFT JOIN weekday_ranking AS w
            ON w.ranking = 1

        WHERE s.location_id = :location_id
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                parameters,
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        logger.warning(
            "Zone details not found: location_id=%s",
            location_id,
        )

        return None

    result = dict(row)

    for field_name in (
        "avg_total_amount",
        "avg_trip_distance",
        "demand_score",
        "hotspot_component_score",
        "consistency_score",
        "zone_score",
    ):
        value = result.get(field_name)

        if value is not None:
            result[field_name] = float(value)

    logger.info(
        "Zone details fetched: location_id=%s zone_score=%s",
        location_id,
        result["zone_score"],
    )

    return result

def fetch_zone_trend(
    location_id: int,
    filters: DashboardFilters,
    period_days: int,
) -> dict[str, Any] | None:
    filter_parameters = filters_to_dict(filters)

    parameters = {
        "location_id": location_id,
        "hour": filter_parameters.get("hour"),
        "weekday": filter_parameters.get("weekday"),
        "date_to": filter_parameters.get("date_to"),
        "period_days": period_days,
    }

    logger.info(
        "Fetching zone trend: location_id=%s "
        "period_days=%s filters=%s",
        location_id,
        period_days,
        filter_parameters,
    )

    query = text(
        """
        WITH dataset_bounds AS (
            SELECT
                MAX(
                    pickup_date
                )::date AS maximum_date

            FROM analytics.zone_hourly_demand

            WHERE (
                CAST(:hour AS SMALLINT) IS NULL
                OR pickup_hour = CAST(:hour AS SMALLINT)
            )
            AND (
                CAST(:weekday AS SMALLINT) IS NULL
                OR EXTRACT(
                    ISODOW FROM pickup_date
                ) = CAST(:weekday AS SMALLINT)
            )
        ),

        period_bounds AS (
            SELECT
                LEAST(
                    COALESCE(
                        CAST(:date_to AS DATE),
                        maximum_date
                    ),
                    maximum_date
                )::date AS current_period_end

            FROM dataset_bounds
        ),

        calculated_periods AS (
            SELECT
                current_period_end,

                (
                    current_period_end
                    - (
                        CAST(:period_days AS INTEGER)
                        - 1
                    )
                )::date AS current_period_start,

                (
                    current_period_end
                    - CAST(:period_days AS INTEGER)
                )::date AS previous_period_end,

                (
                    current_period_end
                    - (
                        CAST(:period_days AS INTEGER)
                        * 2
                        - 1
                    )
                )::date AS previous_period_start

            FROM period_bounds
        ),

        filtered_demand AS (
            SELECT
                d.pickup_date,

                SUM(
                    d.trip_count
                )::bigint AS trip_count

            FROM analytics.zone_hourly_demand AS d

            CROSS JOIN calculated_periods AS p

            WHERE d.location_id = :location_id

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

            AND d.pickup_date
                BETWEEN
                    p.previous_period_start
                AND
                    p.current_period_end

            GROUP BY d.pickup_date
        ),

        period_totals AS (
            SELECT
                p.current_period_start,
                p.current_period_end,
                p.previous_period_start,
                p.previous_period_end,

                COALESCE(
                    SUM(
                        CASE
                            WHEN d.pickup_date
                                BETWEEN
                                    p.current_period_start
                                AND
                                    p.current_period_end
                            THEN d.trip_count
                            ELSE 0
                        END
                    ),
                    0
                )::bigint AS current_period_trip_count,

                COALESCE(
                    SUM(
                        CASE
                            WHEN d.pickup_date
                                BETWEEN
                                    p.previous_period_start
                                AND
                                    p.previous_period_end
                            THEN d.trip_count
                            ELSE 0
                        END
                    ),
                    0
                )::bigint AS previous_period_trip_count

            FROM calculated_periods AS p

            LEFT JOIN filtered_demand AS d
                ON TRUE

            GROUP BY
                p.current_period_start,
                p.current_period_end,
                p.previous_period_start,
                p.previous_period_end
        ),

        calculated_change AS (
            SELECT
                current_period_start,
                current_period_end,
                previous_period_start,
                previous_period_end,
                current_period_trip_count,
                previous_period_trip_count,

                (
                    current_period_trip_count
                    - previous_period_trip_count
                )::bigint AS change_amount,

                CASE
                    WHEN previous_period_trip_count = 0
                        THEN NULL

                    ELSE ROUND(
                        (
                            100.0
                            * (
                                current_period_trip_count
                                - previous_period_trip_count
                            )
                            / previous_period_trip_count
                        )::numeric,
                        2
                    )
                END AS change_percentage

            FROM period_totals
        )

        SELECT
            z.location_id,
            z.zone_name,
            z.borough,

            CAST(
                :period_days AS INTEGER
            ) AS period_days,

            c.current_period_start,
            c.current_period_end,
            c.previous_period_start,
            c.previous_period_end,

            c.current_period_trip_count,
            c.previous_period_trip_count,
            c.change_amount,
            c.change_percentage,

            CASE
                WHEN
                    c.current_period_trip_count = 0
                    AND c.previous_period_trip_count = 0
                    THEN 'Veri Yok'

                WHEN
                    c.previous_period_trip_count = 0
                    AND c.current_period_trip_count > 0
                    THEN 'Yükselen'

                WHEN c.change_percentage > 5
                    THEN 'Yükselen'

                WHEN c.change_percentage < -5
                    THEN 'Düşen'

                ELSE 'Stabil'
            END AS trend_direction

        FROM core.taxi_zones AS z

        CROSS JOIN calculated_change AS c

        WHERE z.location_id = :location_id
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                parameters,
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        logger.warning(
            "Zone trend not found: location_id=%s",
            location_id,
        )

        return None

    result = dict(row)

    if result["change_percentage"] is not None:
        result["change_percentage"] = float(
            result["change_percentage"]
        )

    logger.info(
        "Zone trend fetched: location_id=%s "
        "direction=%s change_percentage=%s",
        location_id,
        result["trend_direction"],
        result["change_percentage"],
    )

    return result

def fetch_zone_anomalies(
    location_id: int,
    filters: DashboardFilters,
    analysis_days: int,
    z_threshold: float,
) -> dict[str, Any] | None:
    filter_parameters = filters_to_dict(filters)

    parameters = {
        "location_id": location_id,
        "hour": filter_parameters.get("hour"),
        "weekday": filter_parameters.get("weekday"),
        "date_to": filter_parameters.get("date_to"),
        "analysis_days": analysis_days,
        "z_threshold": z_threshold,
    }

    logger.info(
        "Fetching zone anomalies: location_id=%s "
        "analysis_days=%s z_threshold=%s filters=%s",
        location_id,
        analysis_days,
        z_threshold,
        filter_parameters,
    )

    query = text(
        """
        WITH dataset_bounds AS (
            SELECT
                MAX(
                    pickup_date
                )::date AS maximum_date

            FROM analytics.zone_hourly_demand

            WHERE location_id = :location_id

            AND (
                CAST(:hour AS SMALLINT) IS NULL
                OR pickup_hour = CAST(:hour AS SMALLINT)
            )

            AND (
                CAST(:weekday AS SMALLINT) IS NULL
                OR EXTRACT(
                    ISODOW FROM pickup_date
                ) = CAST(:weekday AS SMALLINT)
            )
        ),

        analysis_bounds AS (
            SELECT
                LEAST(
                    COALESCE(
                        CAST(:date_to AS DATE),
                        maximum_date
                    ),
                    maximum_date
                )::date AS analysis_end

            FROM dataset_bounds
        ),

        calculated_bounds AS (
            SELECT
                analysis_end,

                (
                    analysis_end
                    - (
                        CAST(:analysis_days AS INTEGER)
                        - 1
                    )
                )::date AS analysis_start

            FROM analysis_bounds
        ),

        calendar_days AS (
            SELECT
                generated_date::date AS pickup_date

            FROM calculated_bounds AS b

            CROSS JOIN LATERAL generate_series(
                b.analysis_start,
                b.analysis_end,
                INTERVAL '1 day'
            ) AS generated_date

            WHERE (
                CAST(:weekday AS SMALLINT) IS NULL
                OR EXTRACT(
                    ISODOW FROM generated_date
                ) = CAST(:weekday AS SMALLINT)
            )
        ),

        daily_demand AS (
            SELECT
                d.pickup_date,

                SUM(
                    d.trip_count
                )::bigint AS trip_count

            FROM analytics.zone_hourly_demand AS d

            CROSS JOIN calculated_bounds AS b

            WHERE d.location_id = :location_id

            AND d.pickup_date
                BETWEEN
                    b.analysis_start
                AND
                    b.analysis_end

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

            GROUP BY d.pickup_date
        ),

        complete_daily_demand AS (
            SELECT
                c.pickup_date,

                COALESCE(
                    d.trip_count,
                    0
                )::bigint AS trip_count

            FROM calendar_days AS c

            LEFT JOIN daily_demand AS d
                ON c.pickup_date = d.pickup_date
        ),

        demand_statistics AS (
            SELECT
                COUNT(*)::integer AS observation_count,

                COALESCE(
                    AVG(trip_count),
                    0
                )::numeric AS mean_daily_trips,

                COALESCE(
                    STDDEV_SAMP(trip_count),
                    0
                )::numeric AS standard_deviation

            FROM complete_daily_demand
        ),

        scored_days AS (
            SELECT
                d.pickup_date,
                d.trip_count,
                s.observation_count,
                s.mean_daily_trips,
                s.standard_deviation,

                (
                    d.trip_count
                    - s.mean_daily_trips
                )::numeric AS deviation_amount,

                CASE
                    WHEN s.mean_daily_trips = 0
                        THEN NULL

                    ELSE (
                        100.0
                        * (
                            d.trip_count
                            - s.mean_daily_trips
                        )
                        / s.mean_daily_trips
                    )::numeric
                END AS deviation_percentage,

                CASE
                    WHEN s.standard_deviation = 0
                        THEN 0

                    ELSE (
                        (
                            d.trip_count
                            - s.mean_daily_trips
                        )
                        / s.standard_deviation
                    )::numeric
                END AS z_score

            FROM complete_daily_demand AS d

            CROSS JOIN demand_statistics AS s
        ),

        anomaly_items AS (
            SELECT
                pickup_date,
                trip_count,

                ROUND(
                    mean_daily_trips,
                    2
                ) AS expected_trip_count,

                ROUND(
                    deviation_amount,
                    2
                ) AS deviation_amount,

                CASE
                    WHEN deviation_percentage IS NULL
                        THEN NULL

                    ELSE ROUND(
                        deviation_percentage,
                        2
                    )
                END AS deviation_percentage,

                ROUND(
                    z_score,
                    2
                ) AS z_score,

                CASE
                    WHEN z_score >= CAST(
                        :z_threshold AS NUMERIC
                    )
                        THEN 'Yüksek Talep'

                    WHEN z_score <= -CAST(
                        :z_threshold AS NUMERIC
                    )
                        THEN 'Düşük Talep'
                END AS anomaly_type

            FROM scored_days

            WHERE ABS(z_score) >= CAST(
                :z_threshold AS NUMERIC
            )

            ORDER BY
                ABS(z_score) DESC,
                pickup_date DESC
        )

        SELECT
            z.location_id,
            z.zone_name,
            z.borough,

            CAST(
                :analysis_days AS INTEGER
            ) AS analysis_days,

            b.analysis_start,
            b.analysis_end,

            s.observation_count,

            ROUND(
                s.mean_daily_trips,
                2
            ) AS mean_daily_trips,

            ROUND(
                s.standard_deviation,
                2
            ) AS standard_deviation,

            CAST(
                :z_threshold AS NUMERIC
            ) AS z_threshold,

            (
                SELECT COUNT(*)::integer
                FROM anomaly_items
            ) AS anomaly_count,

            COALESCE(
                (
                    SELECT JSON_AGG(
                        JSON_BUILD_OBJECT(
                            'pickup_date',
                            a.pickup_date,

                            'trip_count',
                            a.trip_count,

                            'expected_trip_count',
                            a.expected_trip_count,

                            'deviation_amount',
                            a.deviation_amount,

                            'deviation_percentage',
                            a.deviation_percentage,

                            'z_score',
                            a.z_score,

                            'anomaly_type',
                            a.anomaly_type
                        )

                        ORDER BY
                            ABS(a.z_score) DESC,
                            a.pickup_date DESC
                    )

                    FROM anomaly_items AS a
                ),
                '[]'::json
            ) AS items

        FROM core.taxi_zones AS z

        CROSS JOIN calculated_bounds AS b
        CROSS JOIN demand_statistics AS s

        WHERE z.location_id = :location_id
        """
    )

    with engine.connect() as connection:
        row = (
            connection.execute(
                query,
                parameters,
            )
            .mappings()
            .one_or_none()
        )

    if row is None:
        logger.warning(
            "Zone anomalies not found: location_id=%s",
            location_id,
        )

        return None

    result = dict(row)

    for field_name in (
        "mean_daily_trips",
        "standard_deviation",
        "z_threshold",
    ):
        result[field_name] = float(
            result[field_name] or 0
        )

    normalized_items = []

    for item in result.get("items") or []:
        normalized_item = dict(item)

        for field_name in (
            "expected_trip_count",
            "deviation_amount",
            "deviation_percentage",
            "z_score",
        ):
            value = normalized_item.get(field_name)

            if value is not None:
                normalized_item[field_name] = float(value)

        normalized_items.append(normalized_item)

    result["items"] = normalized_items

    logger.info(
        "Zone anomalies fetched: location_id=%s "
        "anomaly_count=%s",
        location_id,
        result["anomaly_count"],
    )

    return result