import logging
from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from config import Environment, get_settings
from fastapi import Depends
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import Session, SQLModel, create_engine

from .settings import DatabaseUrl

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
SQLModel.metadata.naming_convention = NAMING_CONVENTION


def create_db_engine(database_url: DatabaseUrl):
    """create the database engine based on `database_url`"""
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine) -> async_sessionmaker[AsyncSession]:
    """factory used to generate session based on `engine`"""
    return async_sessionmaker(engine, expire_on_commit=False)
