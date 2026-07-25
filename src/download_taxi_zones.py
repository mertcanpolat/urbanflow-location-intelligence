from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import requests

TAXI_ZONES_URL = (
    "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zones.zip"
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "taxi_zones"
ZIP_PATH = RAW_DIR / "taxi_zones.zip"


def download_file(url: str, output_path: Path) -> None:
    """Download a file only when it does not already exist."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logging.info("Dosya zaten mevcut: %s", output_path)
        return

    logging.info("Veri indiriliyor: %s", url)

    response = requests.get(url, timeout=120)
    response.raise_for_status()

    output_path.write_bytes(response.content)

    logging.info(
        "İndirme tamamlandı: %s (%.2f MB)",
        output_path,
        output_path.stat().st_size / 1024 / 1024,
    )


def extract_zip(zip_path: Path, output_dir: Path) -> None:
    """Extract the downloaded Taxi Zone archive."""
    shapefile_path = output_dir / "taxi_zones.shp"

    if shapefile_path.exists():
        logging.info("Veri zaten çıkarılmış: %s", shapefile_path)
        return

    logging.info("ZIP dosyası açılıyor.")

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(output_dir)

    logging.info("Dosyalar çıkarıldı: %s", output_dir)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    download_file(TAXI_ZONES_URL, ZIP_PATH)
    extract_zip(ZIP_PATH, RAW_DIR)


if __name__ == "__main__":
    main()