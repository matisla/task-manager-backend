import logging
from enum import StrEnum
from functools import cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.auth.settings import AuthSettings
from app.db.settings import DatabaseSettings

from .cors import CORSSettings
from .logging import LoggingSettings


class Environment(StrEnum):
    """
    Environment in which the application is running.
    """

    DEV = "development"
    PROD = "production"
    TEST = "test"


class Settings(BaseSettings):
    """
    Global settings
    """

    PROJECT_NAME: str = "Tasks Manager"
    ENVIRONMENT: Environment = Environment.DEV
    DEBUG: bool = False

    # Authentication settings
    auth: AuthSettings = Field(default_factory=AuthSettings)
    db: DatabaseSettings = Field(default_factory=DatabaseSettings)
    log: LoggingSettings = Field(default_factory=LoggingSettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        env_nested_delimiter="_",
        extra="ignore",
    )


@cache
def get_settings(filename: str | Path | None = None) -> Settings:
    """
    Get the settings object with all the settings of the app.

    Args:
        filename (str | Path | None): path of the file to load for the environment.

    Returns:
        Settings: the settings object.
    """
    settings = None

    if filename is not None:
        if not Path(filename).exists():
            raise FileNotFoundError(f"environment file does not exist '{filename}'.")

        load_dotenv(filename)

    settings = Settings()

    settings.log.configure()

    logger = logging.getLogger(__name__)
    logger.debug(f"Settings loaded from {filename or 'default'}")

    return settings


def load_settings(filename: str | Path | None = None) -> Settings:
    """
    Load the settings configuration, bypassing the `get_settings` cache.

    Args:
        filename (str | Path | None): if provided, load this specific env file,
            else use the default parameters.

    Returns:
        Settings: the settings.
    """

    get_settings.cache_clear()

    return get_settings(filename)
