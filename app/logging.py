"""Structured logging setup using structlog.

Configured once at import time. All loggers created via `structlog.get_logger()`
inherit the JSON renderer and stdout processor chain.

Log format: ts=ISO8601 level=INFO/WARN/ERROR logger=name event=message key=value...
"""

from __future__ import annotations

import sys

import structlog

from app.config import settings


def configure_logging() -> None:
    """Call once at application startup (before any worker forks)."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(serializable_default=str),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log level via environment / settings
    if settings.log_level != "INFO":
        # Adjust uvicorn/access loggers
        import logging
        logging.getLogger("uvicorn.access").setLevel(settings.log_level)


# Apply at module import — safe to call multiple times
configure_logging()
