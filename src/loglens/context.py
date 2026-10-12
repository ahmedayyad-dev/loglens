"""Correlation-id storage backed by :mod:`contextvars`.

The value is stored in a :class:`contextvars.ContextVar`, which means it is
naturally scoped to the current task when using :mod:`asyncio`. Every task
spawned from within a :func:`correlation` block inherits a *copy* of the
context, so the id propagates automatically while staying isolated from other
requests/tasks.
"""

from __future__ import annotations

import contextvars
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

__all__ = [
    "clear_correlation_id",
    "correlation",
    "get_correlation_id",
    "new_correlation_id",
    "reset_correlation_id",
    "set_correlation_id",
]

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "loglens_correlation_id", default=None
)


def new_correlation_id() -> str:
    """Return a fresh, URL-safe-ish 32 character hex correlation id."""
    return uuid.uuid4().hex


def get_correlation_id() -> str | None:
    """Return the current correlation id, or ``None`` when unset."""
    return _correlation_id.get()


def set_correlation_id(value: str) -> contextvars.Token[str | None]:
    """Set the correlation id and return a token usable with :func:`reset_correlation_id`."""
    if not value:
        raise ValueError("correlation id must be a non-empty string")
    return _correlation_id.set(value)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    """Restore the correlation id to the value it had before ``token`` was created."""
    _correlation_id.reset(token)


def clear_correlation_id() -> None:
    """Unset the correlation id for the current context."""
    _correlation_id.set(None)


@contextmanager
def correlation(value: str | None = None) -> Iterator[str]:
    """Bind a correlation id for the duration of the ``with`` block.

    When ``value`` is omitted a new id is generated. The id is yielded so it can
    be forwarded to downstream services::

        with loglens.correlation() as cid:
            logger.info("handling request")
            await client.get(url, headers={"X-Request-ID": cid})
    """
    cid = value or new_correlation_id()
    token = _correlation_id.set(cid)
    try:
        yield cid
    finally:
        _correlation_id.reset(token)
