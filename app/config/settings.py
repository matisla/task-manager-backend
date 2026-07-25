from enum import StrEnum

from auth.settings import AuthSettings
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .logging import LoggingSettings


class Environment(StrEnum):
    DEV = "development"
    PROD = "production"
    TEST = "test"


class PostgreSQLSettings(BaseSettings):
    """
    Database PostgreSQL settings
    """

    SERVER: str = Field(default="localhost")
    PORT: int = Field(default=5432)
    USER: str = Field(default="postgres")
    PASSWORD: str = Field(default="postgres")
    DB: str = Field(default="postgres")

    URL: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def connexion_url(self) -> str:
        """
        Build and return the connexion URL for PostgreSQL database.
        Or use the attribute URL if defined

        Returns:
            str: connexion URL
        """

        if self.URL:
            return self.URL

        return f"postgresql://{self.USER}:{self.PASSWORD}@{self.SERVER}:{self.PORT}/{self.DB}"


class Settings(BaseSettings):
    """
    Global settings
    """

    PROJECT_NAME: str = "Tasks Manager"
    ENVIRONMENT: Environment = Environment.DEV
    DEBUG: bool = False

    # Authentication settings
    auth: AuthSettings = AuthSettings()
    db: PostgreSQLSettings = PostgreSQLSettings()
    log: LoggingSettings = LoggingSettings()

    SettingsConfigDict(
        env_prefix="POSTGRES_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        env_nested_delimiter="_",
    )


settings = Settings()
