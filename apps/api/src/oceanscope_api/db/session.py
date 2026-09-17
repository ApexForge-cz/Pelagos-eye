from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from oceanscope_api.core.errors import DatabaseUnavailableError
from oceanscope_api.core.settings import get_settings


@lru_cache
def get_engine() -> Engine:
    database_url = get_settings().database_url
    if database_url is None:
        raise DatabaseUnavailableError("database is not configured")
    return create_engine(database_url.get_secret_value(), pool_pre_ping=True)


def get_session() -> Iterator[Session]:
    try:
        with Session(get_engine()) as session:
            yield session
    except DatabaseUnavailableError:
        raise
    except SQLAlchemyError as error:
        raise DatabaseUnavailableError("database request failed") from error


def database_is_available() -> bool:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (DatabaseUnavailableError, SQLAlchemyError):
        return False
    return True
