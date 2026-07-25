from __future__ import annotations

import logging
import os
from pathlib import Path

import geopandas as gpd
from dotenv import load_dotenv
from geoalchemy2 import Geometry
from shapely.geometry import MultiPolygon
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHAPEFILE_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "taxi_zones"
    / "taxi_zones"
    / "taxi_zones.shp"
)


def create_database_engine():
    """Create a SQLAlchemy engine using environment variables."""
    load_dotenv(PROJECT_ROOT / ".env")

    host = os.environ["DB_HOST"]
    port = os.environ["DB_PORT"]
    database = os.environ["DB_NAME"]
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]

    connection_url = (
        f"postgresql+psycopg://{user}:{password}"
        f"@{host}:{port}/{database}"
    )

    return create_engine(connection_url)


def prepare_data() -> gpd.GeoDataFrame:
    """Read, validate and transform the Taxi Zone source data."""
    gdf = gpd.read_file(SHAPEFILE_PATH)

    logging.info("Ham kayıt sayısı: %s", len(gdf))
    logging.info("Kaynak CRS: %s", gdf.crs)

    column_mapping = {
        "LocationID": "location_id",
        "zone": "zone_name",
        "borough": "borough",
        "Shape_Leng": "shape_length_source",
        "Shape_Area": "shape_area_source",
    }

    gdf = gdf.rename(columns=column_mapping)

    required_columns = {
        "location_id",
        "zone_name",
        "borough",
        "geometry",
    }

    missing_columns = required_columns - set(gdf.columns)

    if missing_columns:
        raise ValueError(
            f"Eksik zorunlu sütunlar: {sorted(missing_columns)}"
        )

    if gdf.crs is None:
        raise ValueError("Kaynak verinin koordinat sistemi tanımlı değil.")

    gdf = gdf.to_crs(epsg=4326)

    gdf["geometry"] = gdf.geometry.make_valid()

    gdf["geometry"] = gdf.geometry.apply(
        lambda geometry: (
            geometry
            if geometry.geom_type == "MultiPolygon"
            else MultiPolygon([geometry])
        )
    )

    gdf["geometry"] = gdf.geometry.apply(
        lambda geometry: (
            geometry
            if geometry.geom_type == "MultiPolygon"
            else __import__("shapely").geometry.MultiPolygon([geometry])
        )
    )

    gdf = gdf[
        [
            "location_id",
            "zone_name",
            "borough",
            "geometry",
        ]
    ].copy()

    gdf["location_id"] = gdf["location_id"].astype("int16")
    gdf["zone_name"] = gdf["zone_name"].astype("string")
    gdf["borough"] = gdf["borough"].astype("string")

    if gdf["location_id"].duplicated().any():
        duplicates = gdf.loc[
            gdf["location_id"].duplicated(keep=False),
            "location_id",
        ].tolist()

        raise ValueError(
            f"Tekrarlanan location_id değerleri bulundu: {duplicates}"
        )

    if gdf[["location_id", "zone_name", "borough", "geometry"]].isna().any().any():
        raise ValueError("Zorunlu alanlarda NULL değer bulundu.")

    if not gdf.geometry.is_valid.all():
        raise ValueError("Geçersiz geometriler düzeltilemedi.")

    logging.info("Hazırlanan kayıt sayısı: %s", len(gdf))
    logging.info("Hedef CRS: %s", gdf.crs)

    return gdf


def load_data(
    gdf: gpd.GeoDataFrame,
) -> None:
    """Load Taxi Zones into a temporary staging table, then upsert to core."""
    engine = create_database_engine()

    with engine.begin() as connection:
        connection.execute(
            text(
                """
                DROP TABLE IF EXISTS staging.taxi_zones_load;
                """
            )
        )

    gdf.to_postgis(
        name="taxi_zones_load",
        con=engine,
        schema="staging",
        if_exists="replace",
        index=False,
        dtype={
            "geometry": Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
            )
        },
    )

    upsert_sql = text(
        """
        INSERT INTO core.taxi_zones (
            location_id,
            zone_name,
            borough,
            service_zone,
            geom
        )
        SELECT
            location_id,
            zone_name,
            borough,
            NULL AS service_zone,
            geometry AS geom
        FROM staging.taxi_zones_load
        ON CONFLICT (location_id)
        DO UPDATE SET
            zone_name = EXCLUDED.zone_name,
            borough = EXCLUDED.borough,
            service_zone = EXCLUDED.service_zone,
            geom = EXCLUDED.geom;
        """
    )

    with engine.begin() as connection:
        result = connection.execute(upsert_sql)

        logging.info(
            "Core tabloya işlenen kayıt sayısı: %s",
            result.rowcount,
        )

        connection.execute(
            text(
                """
                DROP TABLE IF EXISTS staging.taxi_zones_load;
                """
            )
        )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    gdf = prepare_data()
    load_data(gdf)

    logging.info("Taxi Zone yükleme işlemi tamamlandı.")


if __name__ == "__main__":
    main()