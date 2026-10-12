"""Formatters: JSON and dev/colored."""

from __future__ import annotations

import json

from loglens.context import correlation
from loglens.filters import CorrelationIdFilter
from loglens.formatters import DevFormatter, JSONFormatter, extract_extras


def _log_and_get(logs_ctx, level: str, message: str, **extra):
    logger, captured = logs_ctx
    getattr(logger, level)(message, **({"extra": extra} if extra else {}))
    return captured.records[-1]


def test_json_shape(logs) -> None:
    with correlation("abc"):
        record = _log_and_get(logs, "info", "hello", path="/api")
        payload = json.loads(JSONFormatter().format(record))
    assert payload["level"] == "INFO"
    assert payload["logger"] == "loglens.tests"
    assert payload["message"] == "hello"
    assert payload["correlation_id"] == "abc"
    assert payload["path"] == "/api"
    assert "timestamp" in payload


def test_correlation_id_captured_by_filter(logs) -> None:
    with correlation("abc"):
        record = _log_and_get(logs, "info", "hello")
        CorrelationIdFilter().filter(record)
    payload = json.loads(JSONFormatter().format(record))
    assert payload["correlation_id"] == "abc"


def test_json_redacts_secret_extra(logs) -> None:
    record = _log_and_get(logs, "info", "ok", api_key="deadbeef")
    payload = json.loads(JSONFormatter().format(record))
    assert payload["api_key"] == "***"


def test_json_redaction_can_be_disabled(logs) -> None:
    record = _log_and_get(logs, "info", "ok", api_key="deadbeef")
    payload = json.loads(JSONFormatter(redact=False).format(record))
    assert payload["api_key"] == "deadbeef"


def test_json_redacts_message_text(logs) -> None:
    record = _log_and_get(logs, "info", "using Bearer eyJhbGciOiJIUzI1NiJ9.abc.def now")
    payload = json.loads(JSONFormatter().format(record))
    assert "eyJhbGciOiJIUzI1NiJ9" not in payload["message"]


def test_json_includes_exception(logs) -> None:
    logger, captured = logs
    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("failed")
    record = captured.records[-1]
    payload = json.loads(JSONFormatter().format(record))
    assert "Traceback" in payload["exception"]
    assert "ValueError: boom" in payload["exception"]


def test_json_extra_fields(logs) -> None:
    record = _log_and_get(logs, "info", "x")
    payload = json.loads(JSONFormatter(extra_fields={"env": "test"}).format(record))
    assert payload["env"] == "test"


def test_json_is_single_line(logs) -> None:
    record = _log_and_get(logs, "info", "hi")
    assert "\n" not in JSONFormatter().format(record)


def test_extract_extras_skips_reserved(logs) -> None:
    record = _log_and_get(logs, "info", "hi", custom=1)
    assert extract_extras(record) == {"custom": 1}


def test_dev_formatter_plain(logs) -> None:
    with correlation("cid-1"):
        record = _log_and_get(logs, "warning", "oh no", failed=3)
        line = DevFormatter(use_color=False).format(record)
    assert "WARNING" in line
    assert "oh no" in line
    assert "loglens.tests" in line
    assert "cid-1" in line
    assert "failed=3" in line
    assert "\x1b[" not in line


def test_dev_formatter_colored(logs) -> None:
    record = _log_and_get(logs, "error", "bad")
    line = DevFormatter(use_color=True).format(record)
    assert "\x1b[" in line


def test_dev_formatter_redacts_extra(logs) -> None:
    record = _log_and_get(logs, "info", "ok", password="hunter2")
    line = DevFormatter(use_color=False).format(record)
    assert "hunter2" not in line


def test_dev_formatter_exception(logs) -> None:
    logger, captured = logs
    try:
        raise LookupError("nope")
    except LookupError:
        logger.exception("crash")
    line = DevFormatter(use_color=False).format(captured.records[-1])
    assert "Traceback" in line
    assert "LookupError: nope" in line