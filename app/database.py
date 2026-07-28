import logging
from collections.abc import Generator
from functools import cache
from typing import Annotated

from config import Environment, get_settings
from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine


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

    connect_args = (
        {"check_same_thread": False} if settings.ENVIRONMENT == Environment.TEST else {}
    )

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


def init_db():
    """
    Create all tables for the database.
    """

    engine = get_engine()

    logger = logging.getLogger(__name__)
    logger.debug("Initialize Database")

    SQLModel.metadata.create_all(engine)


SessionDep = Annotated[Session, Depends(get_session)]
