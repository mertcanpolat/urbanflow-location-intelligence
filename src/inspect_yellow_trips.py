from __future__ import annotations

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PARQUET_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "yellow_trips"
    / "yellow_tripdata_2026-01.parquet"
)


def main() -> None:
    parquet_file = pq.ParquetFile(PARQUET_PATH)

    print("\n--- Parquet metadata ---")
    print(f"Satır sayısı: {parquet_file.metadata.num_rows:,}")
    print(f"Row group sayısı: {parquet_file.metadata.num_row_groups}")
    print(f"Sütun sayısı: {parquet_file.metadata.num_columns}")

    print("\n--- Şema ---")
    print(parquet_file.schema)

    sample = parquet_file.read_row_group(0).to_pandas().head(10)

    print("\n--- İlk 10 kayıt ---")
    print(sample)

    print("\n--- Sütunlar ---")
    print(sample.columns.tolist())

    print("\n--- Veri tipleri ---")
    print(sample.dtypes)


if __name__ == "__main__":
    main()