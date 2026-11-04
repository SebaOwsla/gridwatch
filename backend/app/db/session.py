"""Lazy database engine and one SQLAlchemy session per request."""

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.db.config import database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(
        database_url(),
        pool_size=20,
        max_overflow=5,
        pool_timeout=5,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
