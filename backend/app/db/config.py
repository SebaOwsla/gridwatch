"""Build the database URL without putting a password in source control."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def database_url() -> URL:
    """Read database settings from the environment or the local .env file."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    password = os.getenv("POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("POSTGRES_PASSWORD is required to run database migrations")

    return URL.create(
        "postgresql+psycopg",
        username=os.getenv("POSTGRES_USER", "gridwatch"),
        password=password,
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "gridwatch"),
    )
