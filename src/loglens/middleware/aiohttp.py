"""aiohttp middleware factory for correlation-id propagation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from aiohttp import web

from ..context import new_correlation_id, reset_correlation_id, set_correlation_id

__all__ = [
    "DEFAULT_HEADER",
    "REQUEST_KEY",
    "correlation_middleware",
    "correlation_middleware_factory",
]

DEFAULT_HEADER = "X-Request-ID"

Handler = Callable[[web.Request], Awaitable[web.StreamResponse]]

REQUEST_KEY: web.RequestKey[str] = web.RequestKey("correlation_id")


def correlation_middleware_factory(
    header_name: str = DEFAULT_HEADER,
    *,
    generator: Callable[[], str] = new_correlation_id,
) -> Callable[[web.Request, Handler], Awaitable[web.StreamResponse]]:
    """Build an aiohttp middleware that propagates a correlation id."""

    @web.middleware
    async def correlation_middleware(
        request: web.Request, handler: Handler
    ) -> web.StreamResponse:
        correlation_id = request.headers.get(header_name) or generator()
        request[REQUEST_KEY] = correlation_id
        token = set_correlation_id(correlation_id)
        try:
            response = await handler(request)
        finally:
            reset_correlation_id(token)
        response.headers[header_name] = correlation_id
        return response

    return correlation_middleware


correlation_middleware = correlation_middleware_factory()
