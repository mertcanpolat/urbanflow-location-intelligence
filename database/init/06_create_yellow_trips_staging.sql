CREATE UNLOGGED TABLE IF NOT EXISTS staging.yellow_trips_load (
    source_row_number BIGINT NOT NULL,

    vendor_id SMALLINT,
    pickup_datetime TIMESTAMPTZ,
    dropoff_datetime TIMESTAMPTZ,

    passenger_count SMALLINT,
    trip_distance NUMERIC(10, 3),

    rate_code_id SMALLINT,
    store_and_fwd_flag CHAR(1),

    pickup_location_id SMALLINT,
    dropoff_location_id SMALLINT,

    payment_type SMALLINT,

    fare_amount NUMERIC(10, 2),
    extra_amount NUMERIC(10, 2),
    mta_tax NUMERIC(10, 2),
    tip_amount NUMERIC(10, 2),
    tolls_amount NUMERIC(10, 2),
    improvement_surcharge NUMERIC(10, 2),
    congestion_surcharge NUMERIC(10, 2),
    airport_fee NUMERIC(10, 2),
    cbd_congestion_fee NUMERIC(10, 2),
    total_amount NUMERIC(10, 2),

    trip_duration_seconds INTEGER,
    pickup_date DATE,
    pickup_hour SMALLINT,

    source_file VARCHAR(100) NOT NULL
);