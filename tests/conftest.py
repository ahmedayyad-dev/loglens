"""Shared pytest fixtures."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import pytest


@dataclass
class CapturedLogs:
    records: list[logging.LogRecord] = field(default_factory=list)


@pytest.fixture
def logs() -> CapturedLogs:
    """Attach a collecting handler to a dedicated logger that does not propagate.

    Returns a ``(logger, capture)`` pair bound to ``loglens.tests``.
    """
    captured = CapturedLogs()

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.records.append(record)

    logger = logging.getLogger("loglens.tests")
    logger.setLevel(logging.DEBUG)
    logger.handlers[:] = [_Handler()]  # type: ignore[list-item]
    logger.propagate = False
    yield logger, captured
    logger.handlers = []
    logger.propagate = True
    logger.propagate = True