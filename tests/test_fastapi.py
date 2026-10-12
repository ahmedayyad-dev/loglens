"""FastAPI/Starlette middleware integration."""

from __future__ import annotations

import asyncio

import fastapi
import pytest
from fastapi.testclient import TestClient

from loglens import get_correlation_id
from loglens.middleware.fastapi import CorrelationIdMiddleware


def build_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.add_middleware(CorrelationIdMiddleware)

    @app.get("/echo")
    async def echo(request: fastapi.Request) -> dict[str, str | None]:
        return {
            "context": get_correlation_id(),
            "state": request.state.correlation_id,
        }

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


def test_propagates_incoming_header(client: TestClient) -> None:
    response = client.get("/echo", headers={"X-Request-ID": "req-001"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "req-001"
    assert response.json() == {"context": "req-001", "state": "req-001"}


def test_generates_when_missing(client: TestClient) -> None:
    response = client.get("/echo")
    cid = response.headers["X-Request-ID"]
    assert cid
    assert response.json() == {"context": cid, "state": cid}


def test_custom_header() -> None:
    app = fastapi.FastAPI()
    app.add_middleware(CorrelationIdMiddleware, header_name="X-Trace-Id")

    @app.get("/")
    async def root(request: fastapi.Request) -> dict[str, str | None]:
        return {"cid": get_correlation_id()}

    response = TestClient(app).get("/", headers={"X-Trace-Id": "tr-9"})
    assert response.json() == {"cid": "tr-9"}
    assert response.headers["X-Trace-Id"] == "tr-9"
    assert "X-Request-ID" not in response.headers


def test_non_http_scopes_passthrough() -> None:
    seen: list[list[str | None]] = []

    async def app(scope, receive, send) -> None:
        seen.append([scope["type"], get_correlation_id()])
        await send({"type": "lifespan.startup.complete"})

    async def receive() -> dict:
        return {}

    async def send(message: dict) -> None:
        seen.append([message["type"], get_correlation_id()])

    async def run() -> None:
        middleware = CorrelationIdMiddleware(app)
        await middleware({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)

    asyncio.run(run())

    assert seen[0][0] == "lifespan"
    assert seen[0][1] is None


def test_async_context_leak_free(client: TestClient) -> None:
    for _ in range(3):
        client.get("/echo")
    assert get_correlation_id() is None