from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CORSSettings(BaseSettings):
    """
    CORS settings
    """

    ALLOW_ORIGINS: list[str] = Field(default=["http://localhost", "http://localhost:8000"])
    ALLOW_CREDENTIALS: bool = Field(default=True)
    ALLOW_METHODS: list[str] = Field(default=["*"])
    ALLOW_HEADERS: list[str] = Field(default=["*"])

    model_config = SettingsConfigDict(
        env_prefix="CORS_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allows(self):
        """
        Build the keyword arguments expected by `CORSMiddleware`.

        Returns:
            dict: the allow_origins/allow_credentials/allow_methods/allow_headers mapping.
        """
        return {
            "allow_origins": self.ALLOW_ORIGINS,
            "allow_credentials": self.ALLOW_CREDENTIALS,
            "allow_methods": self.ALLOW_METHODS,
            "allow_headers": self.ALLOW_HEADERS,
        }
