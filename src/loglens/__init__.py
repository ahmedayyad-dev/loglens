"""loglens - structured logging with correlation ids for asyncio apps.

Minimal example::

    import loglens

    loglens.setup(level="INFO")  # dev colors on a tty, JSON otherwise
    log = loglens.get_logger(__name__)

    with loglens.correlation() as cid:
        log.info("request started", extra={"path": "/api"})
"""

from __future__ import annotations

import logging

from .config import setup, setup_dev, setup_prod
from .context import (
    clear_correlation_id,
    correlation,
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)
from .filters import CorrelationIdFilter
from .formatters import DevFormatter, JSONFormatter
from .redaction import Redactor

try:  # pragma: no cover - importlib metadata may be unavailable
    from importlib.metadata import version as _version

    __version__ = _version("loglens")
except Exception:  # pragma: no cover
    __version__ = "0.1.0"

__all__ = [
    "CorrelationIdFilter",
    "DevFormatter",
    "JSONFormatter",
    "Redactor",
    "clear_correlation_id",
    "correlation",
    "get_correlation_id",
    "get_logger",
    "new_correlation_id",
    "reset_correlation_id",
    "set_correlation_id",
    "setup",
    "setup_dev",
    "setup_prod",
]


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a standard :class:`logging.Logger` named after ``name``.

    Loggers are cheap and hierarchical just like the stdlib ones - prefer one
    logger per module: ``loglens.get_logger(__name__)``.
    """
    return logging.getLogger(name)