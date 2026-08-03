from enum import StrEnum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

type DatabaseUrl = str


class DBType(StrEnum):
    """
    Supported database backends.
    """

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

    ECHO: bool = Field(default=False)
    URL: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="DATABASE_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def connexion_url(self) -> DatabaseUrl:
        """
        Build and return the connexion URL for database.
        Or use the attribute URL if defined

        Returns:
            str: connexion URL
        """

        if self.URL:
            return self.URL

        if self.TYPE == DBType.SQLITE:
            return f"sqlite+aiosqlite:///{self.FILENAME}"

        return f"postgresql+asyncpg://{self.USER}:{self.PASSWORD}@{self.SERVER}:{self.PORT}/{self.NAME}"
