from __future__ import annotations

from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHAPEFILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taxi_zones"
    / "taxi_zones"
    / "taxi_zones.shp"
)


def main() -> None:
    gdf = gpd.read_file(SHAPEFILE_PATH)

    print("\n--- İlk 5 kayıt ---")
    print(gdf.head())

    print("\n--- Sütunlar ---")
    print(gdf.columns.tolist())

    print("\n--- Kayıt sayısı ---")
    print(len(gdf))

    print("\n--- Koordinat sistemi ---")
    print(gdf.crs)

    print("\n--- Geometri tipleri ---")
    print(gdf.geom_type.value_counts())

    print("\n--- Eksik değerler ---")
    print(gdf.isna().sum())

    print("\n--- Kolon veri tipleri ---")
    print(gdf.dtypes)


if __name__ == "__main__":
    main()