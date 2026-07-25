CREATE MATERIALIZED VIEW IF NOT EXISTS
analytics.zone_hourly_demand AS
SELECT
    t.pickup_date,
    t.pickup_hour,
    z.location_id,
    z.zone_name,
    z.borough,
    COUNT(*) AS trip_count,
    ROUND(AVG(t.trip_distance), 3) AS avg_trip_distance,
    ROUND(AVG(t.trip_duration_seconds), 2) AS avg_duration_seconds,
    ROUND(AVG(t.total_amount), 2) AS avg_total_amount,
    ROUND(SUM(t.total_amount), 2) AS total_amount
FROM core.trips AS t
JOIN core.taxi_zones AS z
    ON t.pickup_location_id = z.location_id
GROUP BY
    t.pickup_date,
    t.pickup_hour,
    z.location_id,
    z.zone_name,
    z.borough;

CREATE UNIQUE INDEX IF NOT EXISTS
uq_zone_hourly_demand
ON analytics.zone_hourly_demand (
    pickup_date,
    pickup_hour,
    location_id
);

CREATE INDEX IF NOT EXISTS
idx_zone_hourly_demand_borough
ON analytics.zone_hourly_demand (borough);

CREATE INDEX IF NOT EXISTS
idx_zone_hourly_demand_trip_count
ON analytics.zone_hourly_demand (trip_count DESC);