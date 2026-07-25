from __future__ import annotations

import logging
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "yellow_trips"

YEAR = 2026
MONTH = 1

FILE_NAME = f"yellow_tripdata_{YEAR}-{MONTH:02d}.parquet"
FILE_URL = (
    "https://d37ci6vzurychx.cloudfront.net/"
    f"trip-data/{FILE_NAME}"
)

OUTPUT_PATH = RAW_DIR / FILE_NAME


def download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        logging.info("Dosya zaten mevcut: %s", output_path)
        return

    logging.info("Dosya indiriliyor: %s", url)

    with requests.get(url, stream=True, timeout=180) as response:
        response.raise_for_status()

        with output_path.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)

    logging.info(
        "İndirme tamamlandı: %s — %.2f MB",
        output_path,
        output_path.stat().st_size / 1024 / 1024,
    )


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    download_file(FILE_URL, OUTPUT_PATH)


if __name__ == "__main__":
    main()