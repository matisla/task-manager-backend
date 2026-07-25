import logging
from enum import IntEnum
from logging.config import dictConfig
from pathlib import Path

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class LogLevel(IntEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    CRITICAL = logging.CRITICAL


LOGGING_FORMAT = "%(asctime)s | %(levelname)-8s | %(filename)s - %(message)s"

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s | %(levelname)-8s | %(filename)s - %(message)s",
            "formatTime": "%Y-%m-%d %H:%M:%S",
        },
        "uvicorn": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(message)s",
            "use_colors": None,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "/var/log/app.log",
            "formatter": "default",
            "encoding": "utf-8",
            "when": "midnight",
            "interval": 1,
            "backupCount": 3,
        },
        "uvicorn": {
            "formatter": "uvicorn",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["uvicorn"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
    "root": {
        "handlers": ["console", "file"],
        "propagate": True,
    },
}


class LoggingSettings(BaseSettings):
    """
    Logging simple settings
    """

    LEVEL: str = "INFO"
    FORMAT: str = "%(asctime)s | %(levelname)-15s | %(filename)s - %(message)s"
    CONFIG_FILE: str | None = None

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    def configure(self):
        """
        Configure the logging based on configuration.
        """

        content = None

        if self.CONFIG_FILE:
            filename = Path(self.CONFIG_FILE)

            if not filename.exists():
                raise FileNotFoundError(f"'{self.CONFIG_FILE}' does not exist.")

            if not filename.is_file():
                raise FileNotFoundError(f"'{self.CONFIG_FILE}' is not a file.")

            with open(filename, "r", encoding="utf-8") as fn:
                content = yaml.safe_load(fn.read())

        dictConfig(content or LOGGING_CONFIG)

        root_logger = logging.getLogger()
        root_logger.setLevel(self.LEVEL)
