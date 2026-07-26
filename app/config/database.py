from enum import StrEnum
from typing import Annotated

from fastapi import Depends
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

ENGINE: Engine | None = None


class DBType(StrEnum):
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class DatabaseSettings(BaseSettings):
    """
    Database settings
    """

    TYPE: DBType = Field(default=DBType.SQLITE)
    SERVER: str = Field(default="localhost")
    PORT: int = Field(default=5432)
    USER: str = Field(default="postgres")
    PASSWORD: str = Field(default="postgres")
    NAME: str = Field(default="postgres")
    FILENAME: str = Field(default="")

    URL: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def connexion_url(self) -> str:
        """
        Build and return the connexion URL for database.
        Or use the attribute URL if defined

        Returns:
            str: connexion URL
        """

        if self.URL:
            return self.URL

        if self.TYPE == DBType.SQLITE:
            return f"sqlite://{self.FILENAME}"

        return f"{self.TYPE}://{self.USER}:{self.PASSWORD}@{self.SERVER}:{self.PORT}/{self.NAME}"

    def set_engine(self, debug: bool = False) -> Engine:
        """
        Create the engine based on the given url.

        Args:
            url (str): connexion URL for the database
            debug (bool): if debug echo mode will be activated

        Return:
            (Engine): the created engine
        """
        global ENGINE

        ENGINE = create_engine(
            self.connexion_url,
            echo=debug,
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
