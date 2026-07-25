CREATE TABLE IF NOT EXISTS raw.rejected_yellow_trips (
    rejection_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_file VARCHAR(100) NOT NULL,
    source_row_number BIGINT NOT NULL,
    rejection_reason TEXT NOT NULL,
    raw_record JSONB NOT NULL,
    rejected_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_rejected_trip_source_row
    ON raw.rejected_yellow_trips (
        source_file,
        source_row_number
    );

COMMENT ON TABLE raw.rejected_yellow_trips IS
    'Kalite kurallarını geçemeyen Yellow Taxi kayıtları.';