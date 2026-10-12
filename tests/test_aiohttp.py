"""aiohttp middleware integration."""

from __future__ import annotations

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from loglens import get_correlation_id
from loglens.middleware.aiohttp import (
    REQUEST_KEY,
    correlation_middleware,
    correlation_middleware_factory,
)


def _build_app(header_name: str = "X-Request-ID") -> web.Application:
    middleware = (
        correlation_middleware
        if header_name == "X-Request-ID"
        else correlation_middleware_factory(header_name)
    )
    app = web.Application(middlewares=[middleware])

    async def handler(request: web.Request) -> web.Response:
        return web.json_response(
            {"context": get_correlation_id(), "stored": request[REQUEST_KEY]}
        )

    app.router.add_get("/echo", handler)
    return app


async def test_propagates_incoming_header() -> None:
    client = TestClient(TestServer(_build_app()))
    async with client:
        response = await client.get("/echo", headers={"X-Request-ID": "aio-1"})
        assert response.status == 200
        assert response.headers["X-Request-ID"] == "aio-1"
        payload = await response.json()
        assert payload == {"context": "aio-1", "stored": "aio-1"}
        assert get_correlation_id() is None


async def test_generates_when_missing() -> None:
    client = TestClient(TestServer(_build_app()))
    async with client:
        response = await client.get("/echo")
        cid = response.headers["X-Request-ID"]
        assert cid
        payload = await response.json()
        assert payload == {"context": cid, "stored": cid}


async def test_custom_header() -> None:
    client = TestClient(TestServer(_build_app("X-Trace-Id")))
    async with client:
        response = await client.get("/echo", headers={"X-Trace-Id": "aio-9"})
        assert response.headers["X-Trace-Id"] == "aio-9"
        assert "X-Request-ID" not in response.headers
        payload = await response.json()
        assert payload["context"] == "aio-9"