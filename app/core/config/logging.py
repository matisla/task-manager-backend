import logging
import sys
from enum import IntEnum, StrEnum

import structlog
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


class LogFormat(StrEnum):
    CONSOLE = "console"
    JSON = "json"


class LoggingSettings(BaseSettings):
    """
    Logging settings: verbosity level for structlog's JSON output on stdout.
    """

    LEVEL: str = "INFO"
    FORMAT: LogFormat = Field(default=LogFormat.CONSOLE)

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def configure(self) -> None:
        """
        Configure structlog to render one JSON object per line on stdout, filtered by `LEVEL`.

        Backed by the standard library's logging module (a stdout-only handler with a
        pass-through formatter), so that `add_logger_name` can report each logger's
        dotted module name.

        Raises:
            KeyError: if `LEVEL` is not one of DEBUG, INFO, WARNING, CRITICAL.
        """

        min_level = LogLevel[self.LEVEL.upper()]

        logging.basicConfig(format="%(message)s", stream=sys.stdout, level=min_level)

        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(min_level),
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso"),
                (
                    structlog.processors.JSONRenderer()
                    if self.FORMAT == LogFormat.JSON
                    else structlog.dev.ConsoleRenderer(colors=True)
                ),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
