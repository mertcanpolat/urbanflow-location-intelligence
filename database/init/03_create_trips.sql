-- ============================================================
-- Yellow Taxi yolculuklarının güvenilir ana tablosu
-- ============================================================

CREATE TABLE IF NOT EXISTS core.trips (
    trip_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    vendor_id SMALLINT,

    pickup_datetime TIMESTAMPTZ NOT NULL,
    dropoff_datetime TIMESTAMPTZ NOT NULL,

    passenger_count SMALLINT,
    trip_distance NUMERIC(10, 3),

    rate_code_id SMALLINT,
    store_and_fwd_flag CHAR(1),

    pickup_location_id SMALLINT NOT NULL,
    dropoff_location_id SMALLINT NOT NULL,

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

    source_file VARCHAR(100) NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT fk_trips_pickup_zone
        FOREIGN KEY (pickup_location_id)
        REFERENCES core.taxi_zones (location_id),

    CONSTRAINT fk_trips_dropoff_zone
        FOREIGN KEY (dropoff_location_id)
        REFERENCES core.taxi_zones (location_id),

    CONSTRAINT chk_trip_datetime_order
        CHECK (dropoff_datetime >= pickup_datetime),

    CONSTRAINT chk_trip_distance_nonnegative
        CHECK (trip_distance IS NULL OR trip_distance >= 0),

    CONSTRAINT chk_passenger_count_nonnegative
        CHECK (passenger_count IS NULL OR passenger_count >= 0),

    CONSTRAINT chk_pickup_hour
        CHECK (pickup_hour BETWEEN 0 AND 23),

    CONSTRAINT chk_store_and_fwd_flag
        CHECK (
            store_and_fwd_flag IS NULL
            OR store_and_fwd_flag IN ('Y', 'N')
        )
);

COMMENT ON TABLE core.trips IS
    'Temizlenmiş ve doğrulanmış NYC Yellow Taxi yolculuk kayıtları.';

COMMENT ON COLUMN core.trips.trip_id IS
    'PostgreSQL tarafından otomatik oluşturulan benzersiz yolculuk kimliği.';

COMMENT ON COLUMN core.trips.pickup_location_id IS
    'Yolculuğun başladığı TLC Taxi Zone kimliği.';

COMMENT ON COLUMN core.trips.dropoff_location_id IS
    'Yolculuğun bittiği TLC Taxi Zone kimliği.';

COMMENT ON COLUMN core.trips.trip_duration_seconds IS
    'Bırakış ve alış zamanları arasındaki süre, saniye cinsinden.';

COMMENT ON COLUMN core.trips.source_file IS
    'Kaydın geldiği kaynak Parquet dosyasının adı.';

CREATE INDEX IF NOT EXISTS idx_trips_pickup_datetime
    ON core.trips (pickup_datetime);

CREATE INDEX IF NOT EXISTS idx_trips_pickup_location
    ON core.trips (pickup_location_id);

CREATE INDEX IF NOT EXISTS idx_trips_dropoff_location
    ON core.trips (dropoff_location_id);

CREATE INDEX IF NOT EXISTS idx_trips_pickup_date_hour
    ON core.trips (pickup_date, pickup_hour);