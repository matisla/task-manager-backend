import logging
from enum import IntEnum
from logging.config import dictConfig
from pathlib import Path

import structlog
import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(IntEnum):
    """
    Supported logging verbosity levels.
    """

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

        Raises:
            FileNotFoundError: if `CONFIG_FILE` does not exist or is not a file.
        """

        filename = Path(self.CONFIG_FILE)

        if not filename.exists():
            raise FileNotFoundError(f"'{self.CONFIG_FILE}' does not exist.")

        if not filename.is_file():
            raise FileNotFoundError(f"'{self.CONFIG_FILE}' is not a file.")

        with open(filename, encoding="utf-8") as fn:
            content = yaml.safe_load(fn.read())
            dictConfig(content)

        root_logger = logging.getLogger()
        root_logger.setLevel(self.LEVEL)
        root_logger.debug(f"Logging level set to {self.LEVEL}")

    def configure_logging(self):
        """
        Initialize the logging for structlog
        """

        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
        )
