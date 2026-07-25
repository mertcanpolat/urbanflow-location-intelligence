from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")


def build_database_url() -> str:
    """Create the PostgreSQL connection URL from environment variables."""
    required_variables = [
        "DB_HOST",
        "DB_PORT",
        "DB_NAME",
        "DB_USER",
        "DB_PASSWORD",
    ]

    missing_variables = [
        variable
        for variable in required_variables
        if not os.getenv(variable)
    ]

    if missing_variables:
        raise RuntimeError(
            "Eksik veritabanı ortam değişkenleri: "
            + ", ".join(missing_variables)
        )

    return (
        f"postgresql+psycopg://{os.environ['DB_USER']}:"
        f"{os.environ['DB_PASSWORD']}@"
        f"{os.environ['DB_HOST']}:"
        f"{os.environ['DB_PORT']}/"
        f"{os.environ['DB_NAME']}"
    )


engine: Engine = create_engine(
    build_database_url(),
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)