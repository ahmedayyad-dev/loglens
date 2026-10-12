# loglens

Structured logging with **correlation ids** for `asyncio` / FastAPI / aiohttp
applications. Zero runtime dependencies in the core; production-safe JSON
output, colorful dev output, and automatic redaction of sensitive data.

> لغة عربية: [`README.ar.md`](README.ar.md)

## Features

- **Correlation ids** via `contextvars` – propagate `X-Request-ID` through the
  entire request, including spawned asyncio tasks, with zero thread-safety
  headaches.
- **JSON formatter** for production (`timestamp`, `level`, `logger`, `message`,
  `correlation_id`, `exception`, and any `extra=...` fields).
- **Colored dev formatter** with ANSI output, automatically disabled on
  non-tty streams.
- **One-call setup** – `setup()`, `setup_dev()`, `setup_prod()`, plus
  `LOGLENS_LEVEL`, `LOGLENS_FORMAT`, `LOGLENS_REDACT` env vars.
- **Redaction** of passwords, tokens, JWTs, API keys, private keys,
  credit-card-like numbers and more – configurable and on by default.
- **Framework middleware** for FastAPI/Starlette (server `X-Request-ID` reply)
  and aiohttp.
- Fully typed (`py.typed`), `asyncio`-native, Python **>=3.12**.

## Installation

```bash
pip install loglens                # core (no deps)
pip install "loglens[fastapi]"     # + Starlette/FastAPI middleware typing
pip install "loglens[aiohttp]"     # + aiohttp middleware
pip install "loglens[dev]"         # + test/lint tooling
```

## Quickstart

```python
import loglens

logger = loglens.get_logger(__name__)   # or logging.getLogger(__name__)

loglens.setup(level="INFO")             # dev colors on a tty, JSON otherwise

with loglens.correlation() as cid:
    logger.info("handling request", extra={"path": "/api/users", "method": "GET"})
    # cid is a 32-char hex string, also visible via loglens.get_correlation_id()
```

Dev output:

```
14:03:22 INFO  [a1b2c3...] handling request path=/api/users method=GET
```

The same record formatted as JSON:

```json
{"timestamp": "2026-10-13T12:03:22.123456+00:00", "level": "INFO", "logger": "__main__", "message": "handling request", "correlation_id": "a1b2c3...", "path": "/api/users", "method": "GET"}
```

## Correlation IDs

The id lives in a `contextvars.ContextVar`, so it is scoped to the current
asyncio task and *inherited* by child tasks automatically. No manual passing
through call chains needed.

```python
import asyncio
import loglens

async def fetch(user_id: str) -> None:
    # run inside a separate task, still sees the same correlation id
    logger.info("fetching")

with loglens.correlation("req-42"):
    asyncio.run(asyncio.gather(fetch("u1"), fetch("u2")))

loglens.get_correlation_id()   # None outside any context
```

API: `correlation(value=None)`, `get_correlation_id()`,
`set_correlation_id(value)` / `reset_correlation_id(token)`,
`clear_correlation_id()`, `new_correlation_id()`.

## FastAPI / Starlette

```python
from fastapi import FastAPI, Request
from loglens.middleware.fastapi import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)          # default header: X-Request-ID

@app.get("/")
async def root(request: Request):
    return {"request_id": request.state.correlation_id}
```

The middleware is **pure ASGI**, so `contextvars` work correctly. It:

1. reuses an incoming `X-Request-ID`, or generates a new one;
2. sets the correlation id on the request context (visible to endpoints);
3. echoes the id back in the response headers.

Customize via `CorrelationIdMiddleware(app, header_name="X-Trace-Id")`.

## aiohttp

```python
from aiohttp import web
from loglens.middleware.aiohttp import correlation_middleware, REQUEST_KEY

app = web.Application(middlewares=[correlation_middleware])

async def handler(request):
    return web.json_response({"id": request[REQUEST_KEY]})
```

Or with a custom header:
`correlation_middleware_factory("X-Trace-Id")`.

## Redaction

On by default. Sensitive-looking keys (`password`, `token`, `secret`,
`authorization`, ...) and known secret shapes (`Bearer ...`, JWTs, private key
blocks, credit-card-like numbers) are masked:

```python
from loglens.redaction import Redactor

redactor = Redactor(sensitive_keys={"fiscal_code"})

# raw -> {"user": {"password": "***"}, "fiscal_code": "***"}
redactor.redact({"user": {"password": "hunter2"}, "fiscal_code": "XYZ123"})
```

Disable with `setup(redact=False)` or `JSONFormatter(redact=False)`.

## Hand-tuning the loggers

`setup()` returns the installed handler, so you can dig in:

```python
handler = loglens.setup(level="DEBUG", fmt="json", extra_fields={"env": "prod"})
handler.setFormatter(loglens.JSONFormatter(ensure_ascii=False))
```

Available pieces: `JSONFormatter`, `DevFormatter`, `Redactor`, `setup`,
`setup_dev`, `setup_prod`, `get_logger`.

## Environment variables

| Variable          | Values        | Default   |
|-------------------|---------------|-----------|
| `LOGLENS_LEVEL`   | `DEBUG`...`CRITICAL` | `INFO` |
| `LOGLENS_FORMAT`  | `json` / `dev` | auto (tty → dev) |
| `LOGLENS_REDACT`  | `1` / `true` / `0` / `false` | `1` |

## Development

```bash
uv sync --all-extras
uv run pytest
uv run ruff check
uv run mypy
```

## License

[MIT](LICENSE)