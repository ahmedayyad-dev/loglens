"""Pure ASGI middleware compatible with Starlette and FastAPI.

Because it is a *pure ASGI* middleware (not ``BaseHTTPMiddleware``) it plays
nicely with ``contextvars``: the correlation id set here is visible to your
endpoints and to any task they spawn.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from ..context import new_correlation_id, reset_correlation_id, set_correlation_id

if TYPE_CHECKING:  # pragma: no cover - typing only
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

__all__ = ["CorrelationIdMiddleware"]

DEFAULT_HEADER = "X-Request-ID"


class CorrelationIdMiddleware:
    """Read ``X-Request-ID`` (or generate one) and propagate it via contextvar.

    Usage with FastAPI/Starlette::

        app.add_middleware(CorrelationIdMiddleware)

    The id is echoed back in the response header and stored on
    ``request.state.correlation_id`` for handlers that want it directly.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        header_name: str = DEFAULT_HEADER,
        generator: Callable[[], str] = new_correlation_id,
    ) -> None:
        self.app = app
        self.header_name = header_name
        self.generator = generator
        self._header_key = header_name.lower().encode("latin-1")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        correlation_id: str | None = None
        for key, value in scope.get("headers", []):
            if key == self._header_key:
                correlation_id = value.decode("latin-1")
                break
        if not correlation_id:
            correlation_id = self.generator()

        scope.setdefault("state", {})["correlation_id"] = correlation_id
        token = set_correlation_id(correlation_id)

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self._header_key, correlation_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            reset_correlation_id(token)
