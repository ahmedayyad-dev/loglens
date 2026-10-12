"""Correlation-id context tools."""

from __future__ import annotations

import asyncio

import pytest

from loglens.context import (
    clear_correlation_id,
    correlation,
    get_correlation_id,
    new_correlation_id,
    reset_correlation_id,
    set_correlation_id,
)


def test_default_is_none() -> None:
    assert get_correlation_id() is None


def test_new_correlation_id_is_unique() -> None:
    assert new_correlation_id() != new_correlation_id()
    assert len(new_correlation_id()) == 32


def test_set_get_clear() -> None:
    token = set_correlation_id("abc")
    assert get_correlation_id() == "abc"
    reset_correlation_id(token)
    assert get_correlation_id() is None
    clear_correlation_id()
    assert get_correlation_id() is None


def test_set_rejects_empty() -> None:
    with pytest.raises(ValueError):
        set_correlation_id("")


def test_correlation_generates_and_restores() -> None:
    assert get_correlation_id() is None
    with correlation() as cid:
        assert cid
        assert get_correlation_id() == cid
    assert get_correlation_id() is None


def test_correlation_with_value() -> None:
    with correlation("fixed"):
        assert get_correlation_id() == "fixed"
    assert get_correlation_id() is None


def test_correlation_nesting() -> None:
    with correlation("outer"):
        with correlation("inner"):
            assert get_correlation_id() == "inner"
        assert get_correlation_id() == "outer"
    assert get_correlation_id() is None


def test_correlation_propagates_to_tasks() -> None:
    async def run() -> None:
        with correlation("parent"):
            seen = await asyncio.gather(echo(), echo())
            assert seen == ["parent", "parent"]
        assert get_correlation_id() is None

    async def echo() -> str:
        return get_correlation_id() or ""

    asyncio.run(run())


def test_correlation_isolated_between_tasks() -> None:
    async def run() -> None:
        first = asyncio.create_task(worker("one"))
        second = asyncio.create_task(worker("two"))
        await asyncio.gather(first, second)

    async def worker(cid: str) -> None:
        with correlation(cid):
            await asyncio.sleep(0)
            assert get_correlation_id() == cid

    asyncio.run(run())