import logging
from collections.abc import Generator
from functools import cache
from typing import Annotated

from config import Environment, get_settings
from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

# Explicit naming convention, applied once at import time, so constraint names
# are deterministic across backends (SQLite/Postgres) instead of driver-generated,
# keeping Alembic's autogenerate diffs stable and readable.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = NAMING_CONVENTION


@cache
def get_engine() -> Engine:
    """
    Get the database engine.
    If not created yet, create it based on settings and cache it.

    Returns:
        Engine: the created engine.
    """

    settings = get_settings()
    logger = logging.getLogger(__name__)

    logger.debug(f"Creating the {settings.db.TYPE} database engine.")

    connect_args = {"check_same_thread": False} if settings.ENVIRONMENT == Environment.TEST else {}

    engine = create_engine(
        settings.db.connexion_url,
        echo=settings.db.ECHO,
        connect_args=connect_args,
    )

    if settings.ENVIRONMENT == Environment.TEST:
        logger.debug(f"Database URL:{settings.db.connexion_url}.")
        SQLModel.metadata.create_all(engine, checkfirst=True)

    return engine


def get_session() -> Generator[Session]:
    """
    Session generator, used as a FastAPI dependency (see `SessionDep`).

    Yields:
        Session: a database session, closed once the request completes.
    """

    engine = get_engine()

    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
