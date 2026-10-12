"""Log filters used by :mod:`loglens`."""

from __future__ import annotations

import logging

from .context import get_correlation_id

__all__ = ["CorrelationIdFilter"]


class CorrelationIdFilter(logging.Filter):
    """Stamp the current correlation id onto every matching record.

    The id is captured at emit time (the record is created inside the request
    context), so formatters keep working even if the record is formatted later
    or on another thread - far more robust than reading a contextvar at format
    time.
    """

    def __init__(self, *, aware: str = "correlation_id") -> None:
        super().__init__()
        self.aware = aware

    def filter(self, record: logging.LogRecord) -> bool:
        correlation_id = get_correlation_id()
        if correlation_id is not None:
            setattr(record, self.aware, correlation_id)
        return True