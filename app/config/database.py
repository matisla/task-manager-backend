from typing import Annotated
from fastapi import Depends

from sqlmodel import create_engine, Session
from sqlalchemy.engine import Engine

from .settings import settings


ENGINE: Engine | None = None


def set_engine(url: str) -> Engine:
    """
    Create the engine based on the given url.

    Args:
        url (str): connexion URL for the database

    Return:
        (Engine): the created engine
    """
    global ENGINE

    ENGINE = create_engine(
        url,
        echo=settings.DEBUG,
        connect_args={},
    )

    return ENGINE


def init_db():
    """create all tables for database"""

    if ENGINE is None:
        raise ValueError("Database engine not initialized")

    SQLModel.metadata.create_all(ENGINE)


def get_session():
    """Session generator"""

    if ENGINE is None:
        raise ValueError("Database engine not initialized")

    with Session(ENGINE) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
