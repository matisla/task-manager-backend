import logging
from pathlib import Path


from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class LogLevel(StrEnum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    CRITICAL = logging.CRITICAL


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s | %(levelname)-15s | %(filename)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "use_colors": None,
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
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
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
        "": {
                "handler": ["default"], "level": "DEBUG", "propagate": True),
            }
        "uvicorn": {"handlers": ["uvicorn"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}

class LoggingSettings(BaseSettings):
    """
    Logging simple settings
    """

    LEVEL: LogLevel = LogLevel.INFO
    FORMAT: str = "%(asctime)s | %(levelname)-15s | %(filename)s - %(message)s"
    CONFIG_FILE: str | None = None


    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    def configure(self) -> str:
        """
        Configure the logging based on configuration.
        """

        if self.CONFIG_FILE:
            filename = Path(self.CONFIG_FILE)

            if not filename.exists():
                raise FileNotFoundError(f"'{self.CONFIG_FILE}' does not exist.")

        else:
            logging.config.dictConfig(LOGGING_CONFIG)
            logging.setLevel(self.LEVEL)
