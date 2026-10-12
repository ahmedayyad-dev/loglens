# loglens

مكتبة سَجْل منظمة (structured logging) مع **correlation id** لتطبيقات asyncio وFastAPI وaiohttp. النواة بدون أي تبعيات تشغيل.

## المميزات

- **Correlation id** عبر `contextvars` — ينتشر تلقائيًا في كل المهام الفرعية، بدون معاملات يدوية.
- **JSON formatter** للإنتاج + **ملوَّن** للتطوير (يُطفأ تلقائيًا خارج الطرفية).
- **إخفاء تلقائي** للبيانات الحساسة: كلمات المرور، التوكنات، JWTs، مفاتيح API، مفاتيح خاصة، والمزيد.
- **إعداد بسطر واحد**: `setup()` / `setup_dev()` / `setup_prod()` + متغيرات بيئة.
- **Middleware** جاهزة لـ FastAPI/Starlette و aiohttp.
- Python ≥ 3.12، ومكتوبة بالكامل مع Type hints.

## الاستخدام السريع

```python
import loglens

loglens.setup(level="INFO")            # ألوان في التطوير، JSON في الإنتاج
logger = loglens.get_logger(__name__)

with loglens.correlation() as cid:
    logger.info("معالجة طلب", extra={"path": "/api", "method": "GET"})
```

## التكامل مع FastAPI

```python
from fastapi import FastAPI, Request
from loglens.middleware.fastapi import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)

@app.get("/")
async def root(request: Request):
    return {"request_id": request.state.correlation_id}
```

يقرأ الهيدر `X-Request-ID` أو يولّده، يضعه في السياق، ويرجّعه في هيدر الرد.

## التكامل مع aiohttp

```python
from aiohttp import web
from loglens.middleware.aiohttp import correlation_middleware

app = web.Application(middlewares=[correlation_middleware])
```

## التثبيت

```bash
pip install loglens
# أو مع التكاملات:
pip install "loglens[fastapi]" "loglens[aiohttp]"
```

## متغيرات البيئة

| المتغير | القيم | الافتراضي |
|---|---|---|
| `LOGLENS_LEVEL` | `DEBUG`...`CRITICAL` | `INFO` |
| `LOGLENS_FORMAT` | `json` / `dev` | تلقائي |
| `LOGLENS_REDACT` | `1` / `0` | `1` |

## التطوير

```bash
uv sync --all-extras
uv run pytest
uv run ruff check
uv run mypy
```

## الرخصة

MIT — انظر [LICENSE](LICENSE).