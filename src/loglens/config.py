"""One-call configuration helpers for :mod:`loglens`."""

from __future__ import annotations

import logging
import os
import sys
from typing import IO, Any, Literal

from .filters import CorrelationIdFilter
from .formatters import DevFormatter, JSONFormatter
from .redaction import Redactor

__all__ = ["resolve_format", "setup", "setup_dev", "setup_prod"]

Format = Literal["auto", "json", "dev"]

_HANDLER_FLAG = "_loglens_handler"
_TRUTHY = {"1", "true", "yes", "on"}


def _env_bool(name: str, default: bool | None) -> bool | None:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUTHY


def _resolve_level(level: int | str) -> int:
    if isinstance(level, int):
        return level
    resolved = logging.getLevelNamesMapping().get(level.upper())
    if resolved is None:
        raise ValueError(f"unknown log level: {level!r}")
    return resolved


def resolve_format(fmt: Format, stream: IO[str]) -> Format:
    """Resolve ``"auto"`` to ``"dev"`` on a tty, ``"json"`` otherwise."""
    if fmt != "auto":
        return fmt
    env = os.environ.get("LOGLENS_FORMAT")
    if env in ("json", "dev"):
        return env  # type: ignore[return-value]
    return "dev" if stream.isatty() else "json"


def setup(
    level: int | str = "INFO",
    *,
    fmt: Format = "auto",
    json: bool | None = None,
    redact: bool | None = None,
    stream: IO[str] | None = None,
    logger_name: str | None = None,
    redactor: Redactor | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> logging.Handler:
    """Configure a :class:`logging.Handler` and install it on a logger.

    Args:
        level: log level as a name or numeric value.
        fmt: ``"auto"`` (default), ``"json"`` or ``"dev"``.
        json: explicit override for ``fmt`` (``True`` -> json, ``False`` -> dev).
        redact: whether to mask sensitive data (env ``LOGLENS_REDACT`` otherwise).
        stream: destination stream, defaults to ``sys.stderr``.
        logger_name: logger to configure, defaults to the root logger.
        redactor: a pre-built :class:`~loglens.redaction.Redactor`.
        extra_fields: static fields merged into every JSON record.

    Returns:
        The installed handler.
    """
    if isinstance(level, str):
        level = os.environ.get("LOGLENS_LEVEL", level)

    target = logging.getLogger(logger_name)
    target.setLevel(_resolve_level(level))

    stream = stream if stream is not None else sys.stderr

    if json is not None:
        fmt = "json" if json else "dev"
    resolved = resolve_format(fmt, stream)

    if redact is None:
        redact = _env_bool("LOGLENS_REDACT", True)

    for existing in list(target.handlers):
        if getattr(existing, _HANDLER_FLAG, False):
            target.removeHandler(existing)

    handler = logging.StreamHandler(stream)
    setattr(handler, _HANDLER_FLAG, True)
    handler.setLevel(_resolve_level(level))
    handler.addFilter(CorrelationIdFilter())

    if resolved == "json":
        handler.setFormatter(
            JSONFormatter(redact=bool(redact), redactor=redactor, extra_fields=extra_fields)
        )
    else:
        handler.setFormatter(DevFormatter(redact=bool(redact), redactor=redactor))

    target.addHandler(handler)
    return handler


def setup_dev(level: int | str = "DEBUG", **kwargs: Any) -> logging.Handler:
    """Convenience preset for local development (colored text)."""
    kwargs.setdefault("json", False)
    return setup(level, **kwargs)


def setup_prod(level: int | str = "INFO", **kwargs: Any) -> logging.Handler:
    """Convenience preset for production (JSON)."""
    kwargs.setdefault("json", True)
    return setup(level, **kwargs)
