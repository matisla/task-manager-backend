from enum import StrEnum

from auth.settings import AuthSettings
from pydantic_settings import BaseSettings, SettingsConfigDict

from .database import DatabaseSettings
from .logging import LoggingSettings


class Environment(StrEnum):
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
    auth: AuthSettings = AuthSettings()
    db: DatabaseSettings = DatabaseSettings()
    log: LoggingSettings = LoggingSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        env_nested_delimiter="_",
    )


settings = Settings()
