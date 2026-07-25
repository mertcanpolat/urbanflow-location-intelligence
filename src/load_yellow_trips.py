from __future__ import annotations

import json
import logging
import os
from io import StringIO
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "yellow_trips"
    / "yellow_tripdata_2026-01.parquet"
)

BATCH_SIZE = 100_000

EXPECTED_COLUMNS = {
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "store_and_fwd_flag",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
}

STAGING_COLUMNS = [
    "source_row_number",
    "vendor_id",
    "pickup_datetime",
    "dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "rate_code_id",
    "store_and_fwd_flag",
    "pickup_location_id",
    "dropoff_location_id",
    "payment_type",
    "fare_amount",
    "extra_amount",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "congestion_surcharge",
    "airport_fee",
    "cbd_congestion_fee",
    "total_amount",
    "trip_duration_seconds",
    "pickup_date",
    "pickup_hour",
    "source_file",
]


def get_connection() -> psycopg.Connection:
    load_dotenv(PROJECT_ROOT / ".env")

    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
    )


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Kaynak sütunlarını proje standardına dönüştürür."""
    rename_map = {
        "VendorID": "vendor_id",
        "tpep_pickup_datetime": "pickup_datetime",
        "tpep_dropoff_datetime": "dropoff_datetime",
        "passenger_count": "passenger_count",
        "trip_distance": "trip_distance",
        "RatecodeID": "rate_code_id",
        "store_and_fwd_flag": "store_and_fwd_flag",
        "PULocationID": "pickup_location_id",
        "DOLocationID": "dropoff_location_id",
        "payment_type": "payment_type",
        "fare_amount": "fare_amount",
        "extra": "extra_amount",
        "mta_tax": "mta_tax",
        "tip_amount": "tip_amount",
        "tolls_amount": "tolls_amount",
        "improvement_surcharge": "improvement_surcharge",
        "congestion_surcharge": "congestion_surcharge",
        "Airport_fee": "airport_fee",
        "airport_fee": "airport_fee",
        "cbd_congestion_fee": "cbd_congestion_fee",
        "total_amount": "total_amount",
    }

    df = df.rename(columns=rename_map)

    optional_columns = [
        "congestion_surcharge",
        "airport_fee",
        "cbd_congestion_fee",
    ]

    for column in optional_columns:
        if column not in df.columns:
            df[column] = pd.NA

    return df


def prepare_batch(
    df: pd.DataFrame,
    starting_row_number: int,
    source_file: str,
    valid_zone_ids: set[int],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Batch'i temizler ve geçerli/geçersiz olarak ayırır."""
    df = standardize_columns(df.copy())

    df["source_row_number"] = range(
        starting_row_number,
        starting_row_number + len(df),
    )

    # TLC zamanları New York yerel saatidir.
    for column in ["pickup_datetime", "dropoff_datetime"]:
        values = pd.to_datetime(df[column], errors="coerce")

        if values.dt.tz is None:
            values = values.dt.tz_localize(
                "America/New_York",
                ambiguous="NaT",
                nonexistent="NaT",
            )

        df[column] = values.dt.tz_convert("UTC")

    integer_columns = [
        "vendor_id",
        "passenger_count",
        "rate_code_id",
        "pickup_location_id",
        "dropoff_location_id",
        "payment_type",
    ]

    for column in integer_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).astype("Int64")

    numeric_columns = [
        "trip_distance",
        "fare_amount",
        "extra_amount",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "congestion_surcharge",
        "airport_fee",
        "cbd_congestion_fee",
        "total_amount",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df["store_and_fwd_flag"] = (
        df["store_and_fwd_flag"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    duration = (
        df["dropoff_datetime"] - df["pickup_datetime"]
    ).dt.total_seconds()

    df["trip_duration_seconds"] = duration.round().astype("Int64")

    # UTC'ye çevirmeden önceki iş saatini korumak için
    # tekrar New York saatine dönüyoruz.
    pickup_local = df["pickup_datetime"].dt.tz_convert(
        "America/New_York"
    )

    df["pickup_date"] = pickup_local.dt.date
    df["pickup_hour"] = pickup_local.dt.hour.astype("Int64")
    df["source_file"] = source_file

    reasons = pd.Series("", index=df.index, dtype="string")

    def add_reason(mask: pd.Series, reason: str) -> None:
        nonlocal reasons

        reasons.loc[mask] = (
            reasons.loc[mask]
            .where(reasons.loc[mask] == "", reasons.loc[mask] + "; ")
            + reason
        )

    add_reason(
        df["pickup_datetime"].isna(),
        "pickup_datetime_missing_or_invalid",
    )

    add_reason(
        df["dropoff_datetime"].isna(),
        "dropoff_datetime_missing_or_invalid",
    )

    add_reason(
        df["dropoff_datetime"] < df["pickup_datetime"],
        "dropoff_before_pickup",
    )

    add_reason(
        df["trip_distance"].notna()
        & (df["trip_distance"] < 0),
        "negative_trip_distance",
    )

    add_reason(
        df["passenger_count"].notna()
        & (df["passenger_count"] < 0),
        "negative_passenger_count",
    )

    add_reason(
        ~df["pickup_location_id"].isin(valid_zone_ids),
        "invalid_pickup_location_id",
    )

    add_reason(
        ~df["dropoff_location_id"].isin(valid_zone_ids),
        "invalid_dropoff_location_id",
    )

    add_reason(
        df["store_and_fwd_flag"].notna()
        & ~df["store_and_fwd_flag"].isin(["Y", "N"]),
        "invalid_store_and_fwd_flag",
    )

    invalid_mask = reasons != ""

    rejected = df.loc[invalid_mask].copy()
    rejected["rejection_reason"] = reasons.loc[invalid_mask]

    valid = df.loc[~invalid_mask, STAGING_COLUMNS].copy()

    return valid, rejected


def dataframe_to_csv_buffer(
    df: pd.DataFrame,
    columns: list[str],
) -> StringIO:
    """COPY için PostgreSQL uyumlu CSV tamponu üretir."""
    buffer = StringIO()

    df.to_csv(
        buffer,
        columns=columns,
        index=False,
        header=False,
        na_rep="\\N",
    )

    buffer.seek(0)
    return buffer


def copy_valid_rows(
    connection: psycopg.Connection,
    valid: pd.DataFrame,
) -> None:
    if valid.empty:
        return

    buffer = dataframe_to_csv_buffer(valid, STAGING_COLUMNS)

    column_sql = ", ".join(STAGING_COLUMNS)

    copy_sql = f"""
        COPY staging.yellow_trips_load ({column_sql})
        FROM STDIN
        WITH (
            FORMAT CSV,
            NULL '\\N'
        )
    """

    with connection.cursor() as cursor:
        with cursor.copy(copy_sql) as copy:
            while chunk := buffer.read(1024 * 1024):
                copy.write(chunk)


def save_rejected_rows(
    connection: psycopg.Connection,
    rejected: pd.DataFrame,
    source_file: str,
) -> None:
    if rejected.empty:
        return

    records = []

    for _, row in rejected.iterrows():
        raw_record = {}

        for key, value in row.items():
            if pd.isna(value):
                raw_record[key] = None
            elif isinstance(value, pd.Timestamp):
                raw_record[key] = value.isoformat()
            else:
                raw_record[key] = value

        records.append(
            (
                source_file,
                int(row["source_row_number"]),
                str(row["rejection_reason"]),
                json.dumps(raw_record, default=str),
            )
        )

    sql = """
        INSERT INTO raw.rejected_yellow_trips (
            source_file,
            source_row_number,
            rejection_reason,
            raw_record
        )
        VALUES (%s, %s, %s, %s::jsonb)
        ON CONFLICT (
            source_file,
            source_row_number
        )
        DO UPDATE SET
            rejection_reason = EXCLUDED.rejection_reason,
            raw_record = EXCLUDED.raw_record,
            rejected_at = NOW()
    """

    with connection.cursor() as cursor:
        cursor.executemany(sql, records)


def move_staging_to_core(
    connection: psycopg.Connection,
) -> int:
    sql = """
        INSERT INTO core.trips (
            vendor_id,
            pickup_datetime,
            dropoff_datetime,
            passenger_count,
            trip_distance,
            rate_code_id,
            store_and_fwd_flag,
            pickup_location_id,
            dropoff_location_id,
            payment_type,
            fare_amount,
            extra_amount,
            mta_tax,
            tip_amount,
            tolls_amount,
            improvement_surcharge,
            congestion_surcharge,
            airport_fee,
            cbd_congestion_fee,
            total_amount,
            trip_duration_seconds,
            pickup_date,
            pickup_hour,
            source_file,
            source_row_number
        )
        SELECT
            vendor_id,
            pickup_datetime,
            dropoff_datetime,
            passenger_count,
            trip_distance,
            rate_code_id,
            store_and_fwd_flag,
            pickup_location_id,
            dropoff_location_id,
            payment_type,
            fare_amount,
            extra_amount,
            mta_tax,
            tip_amount,
            tolls_amount,
            improvement_surcharge,
            congestion_surcharge,
            airport_fee,
            cbd_congestion_fee,
            total_amount,
            trip_duration_seconds,
            pickup_date,
            pickup_hour,
            source_file,
            source_row_number
        FROM staging.yellow_trips_load
        ON CONFLICT (
            source_file,
            source_row_number
        )
        DO NOTHING
    """

    with connection.cursor() as cursor:
        cursor.execute(sql)
        return cursor.rowcount

def refresh_analytics_views(
    connection: psycopg.Connection,
) -> None:
    """Dashboard tarafından kullanılan materialized view'ları yeniler."""

    logging.info(
        "Materialized view yenileniyor: "
        "analytics.zone_hourly_demand"
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            REFRESH MATERIALIZED VIEW
                analytics.zone_hourly_demand
            """
        )

    logging.info(
        "Materialized view yenilendi: "
        "analytics.zone_hourly_demand"
    )

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    if not PARQUET_PATH.exists():
        raise FileNotFoundError(
            f"Parquet dosyası bulunamadı: {PARQUET_PATH}"
        )

    parquet_file = pq.ParquetFile(PARQUET_PATH)
    source_columns = set(parquet_file.schema.names)

    missing_columns = EXPECTED_COLUMNS - source_columns

    if missing_columns:
        raise ValueError(
            f"Kaynak Parquet dosyasında eksik sütunlar var: "
            f"{sorted(missing_columns)}"
        )

    source_file = PARQUET_PATH.name
    total_source_rows = parquet_file.metadata.num_rows

    logging.info("Kaynak dosya: %s", source_file)
    logging.info("Toplam kaynak satırı: %s", f"{total_source_rows:,}")

    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT location_id FROM core.taxi_zones"
            )

            valid_zone_ids = {
                row[0] for row in cursor.fetchall()
            }

            cursor.execute(
                "TRUNCATE TABLE staging.yellow_trips_load"
            )

        connection.commit()

        processed_rows = 0
        total_valid = 0
        total_rejected = 0

        for batch_number, arrow_batch in enumerate(
            parquet_file.iter_batches(batch_size=BATCH_SIZE),
            start=1,
        ):
            batch_df = arrow_batch.to_pandas()

            valid, rejected = prepare_batch(
                batch_df,
                starting_row_number=processed_rows + 1,
                source_file=source_file,
                valid_zone_ids=valid_zone_ids,
            )

            copy_valid_rows(connection, valid)
            save_rejected_rows(
                connection,
                rejected,
                source_file,
            )

            connection.commit()

            processed_rows += len(batch_df)
            total_valid += len(valid)
            total_rejected += len(rejected)

            logging.info(
                "Batch %s | İşlenen: %s/%s | "
                "Geçerli: %s | Reddedilen: %s",
                batch_number,
                f"{processed_rows:,}",
                f"{total_source_rows:,}",
                f"{len(valid):,}",
                f"{len(rejected):,}",
            )

        inserted_rows = move_staging_to_core(connection)
        connection.commit()

        with connection.cursor() as cursor:
            cursor.execute(
                "TRUNCATE TABLE staging.yellow_trips_load"
            )

        connection.commit()

        refresh_analytics_views(connection)
        connection.commit()

        logging.info("Toplam geçerli kayıt: %s", f"{total_valid:,}")
        logging.info(
            "Toplam reddedilen kayıt: %s",
            f"{total_rejected:,}",
        )
        logging.info(
            "Core tabloya yeni eklenen kayıt: %s",
            f"{inserted_rows:,}",
        )

    except Exception:
        connection.rollback()
        logging.exception("Yellow Taxi yükleme işlemi başarısız.")
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    main()