"""Log formatters: machine-readable JSON for production, colored text for dev."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from .context import get_correlation_id
from .redaction import Redactor

__all__ = ["DevFormatter", "JSONFormatter", "extract_extras"]

# Attributes that :class:`logging.LogRecord` always carries; anything else was
# supplied through ``extra=`` and should be surfaced as structured data.
_RESERVED_ATTRS: frozenset[str] = frozenset(
    {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "message",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    }
)


def extract_extras(record: logging.LogRecord) -> dict[str, Any]:
    """Return the custom fields attached to ``record`` via ``extra=``."""
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED_ATTRS and not key.startswith("_")
    }


class JSONFormatter(logging.Formatter):
    """Render records as single-line JSON objects."""

    def __init__(
        self,
        *,
        redact: bool = True,
        redactor: Redactor | None = None,
        extra_fields: dict[str, Any] | None = None,
        ensure_ascii: bool = False,
    ) -> None:
        super().__init__()
        if redactor is not None:
            self.redactor: Redactor | None = redactor
        else:
            self.redactor = Redactor() if redact else None
        self.extra_fields = dict(extra_fields) if extra_fields else {}
        self.ensure_ascii = ensure_ascii

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
        if correlation_id is not None:
            payload["correlation_id"] = correlation_id

        payload.update(extract_extras(record))

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack_info"] = self.formatStack(record.stack_info)

        payload.update(self.extra_fields)

        if self.redactor is not None:
            payload = self.redactor.redact(payload)

        return json.dumps(payload, ensure_ascii=self.ensure_ascii, default=str)


_RESET = "\x1b[0m"
_DIM = "\x1b[2m"
_BOLD = "\x1b[1m"
_COLORS = {
    "DEBUG": "\x1b[36m",
    "INFO": "\x1b[32m",
    "WARNING": "\x1b[33m",
    "ERROR": "\x1b[31m",
    "CRITICAL": "\x1b[1;41m",
}


class DevFormatter(logging.Formatter):
    """Human-friendly, optionally colored formatter intended for development."""

    def __init__(
        self,
        *,
        use_color: bool | None = None,
        redact: bool = True,
        redactor: Redactor | None = None,
    ) -> None:
        super().__init__()
        self.use_color = sys.stderr.isatty() if use_color is None else use_color
        if redactor is not None:
            self.redactor: Redactor | None = redactor
        else:
            self.redactor = Redactor() if redact else None

    def _paint(self, text: str, code: str) -> str:
        if not self.use_color:
            return text
        return f"{code}{text}{_RESET}"

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        if self.redactor is not None:
            message = self.redactor.redact_text(message)

        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S")
        level = f"{record.levelname:<8}"
        level = self._paint(level, _COLORS.get(record.levelname, ""))

        head = f"{self._paint(timestamp, _DIM)} {level} {self._paint(record.name, _BOLD)}"

        correlation_id = getattr(record, "correlation_id", None) or get_correlation_id()
        if correlation_id is not None:
            head += " " + self._paint(f"[{correlation_id}]", _DIM)

        line = f"{head} {message}"

        extras = extract_extras(record)
        if extras:
            rendered = []
            for key, value in extras.items():
                if self.redactor is not None:
                    if self.redactor.is_sensitive_key(key):
                        value = self.redactor.mask
                    else:
                        value = self.redactor.redact(value)
                rendered.append(f"{key}={value!r}")
            line += " " + self._paint(" ".join(rendered), _DIM)

        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        if record.stack_info:
            line += "\n" + self.formatStack(record.stack_info)

        return line
