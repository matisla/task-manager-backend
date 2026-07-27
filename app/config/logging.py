import logging
from enum import IntEnum
from logging.config import dictConfig
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    CRITICAL = logging.CRITICAL


class LoggingSettings(BaseSettings):
    """
    Logging simple settings
    """

    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s | %(levelname)-15s | %(filename)s - %(message)s"
    CONFIG_FILE: str = Field(default="logging.yaml")

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def configure(self):
        """
        Configure the logging based on configuration.
        """

        filename = Path(self.CONFIG_FILE)

        if not filename.exists():
            raise FileNotFoundError(f"'{self.CONFIG_FILE}' does not exist.")

        if not filename.is_file():
            raise FileNotFoundError(f"'{self.CONFIG_FILE}' is not a file.")

        with open(filename, "r", encoding="utf-8") as fn:
            content = yaml.safe_load(fn.read())
            dictConfig(content)

        root_logger = logging.getLogger()
        root_logger.setLevel(self.LEVEL)
        root_logger.info(f"Logging level: {self.LEVEL}")
