from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """
    Auth settings
    """

    SECRET_KEY: str = Field(
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"),
        default="0acabbc0adaaab03b8dac2dd73c2b56d91a66051752a3f30a2ca7d6d0c849943",
    )
    """secret key, don't forget to change it in production"""

    ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15  # minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # days

    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        env_file_encoding="utf-8",
        extra="ignore",
    )
