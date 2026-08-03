from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from .settings import DatabaseUrl


def create_db_engine(database_url: DatabaseUrl, echo: bool = False):
    """create the database engine based on `database_url`"""
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """factory used to generate session based on `engine`"""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
