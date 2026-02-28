"""
Logging configuration for rs3-tracker.

Import and call configure_logging() once at startup (done in app lifespan).
All other modules should obtain their logger via get_logger(__name__).

Log level is controlled by the LOG_LEVEL environment variable (default: INFO).
"""

import logging
import os

_CONFIGURED = False

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def configure_logging() -> None:
    """Configure the root logger. Safe to call multiple times."""
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )

    # Silence overly chatty third-party loggers at WARNING unless debug is on.
    if level > logging.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger. Call as get_logger(__name__)."""
    return logging.getLogger(name)
