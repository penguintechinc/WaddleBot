"""
Pytest fixtures for flask_core stream-pipeline compliance tests.

Loads `stream_pipeline.py` directly by file path so tests do not have to
import the `flask_core` package (whose `__init__.py` pulls in pydal,
authlib and other unrelated runtime deps not needed here). Provides a
minimal in-memory async fake of `redis.asyncio.Redis` covering only the
Streams commands `StreamPipeline` issues -- no new dependency is added;
`redis` itself remains the only package required (already declared in
`libs/flask_core/requirements.txt`).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Optional

import pytest
import pytest_asyncio

_STREAM_PIPELINE_PATH = (
    Path(__file__).resolve().parents[2]
    / "libs" / "flask_core" / "flask_core" / "stream_pipeline.py"
)


def _load_stream_pipeline_module():
    """Import stream_pipeline.py by path, isolated from the flask_core package."""
    module_name = "waddlebot_stream_pipeline_under_test"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, _STREAM_PIPELINE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


stream_pipeline = _load_stream_pipeline_module()


class FakeAsyncRedis:
    """In-memory async fake of redis.asyncio.Redis, Streams subset only.

    Implements XADD (with real MAXLEN-trim semantics), XTRIM, XLEN and
    XRANGE -- exactly what StreamPipeline calls -- so retention tests
    exercise genuine eviction behaviour without a live Redis server. Not a
    general Redis reimplementation: no consumer groups, no other types.
    """

    def __init__(self) -> None:
        self._streams: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self._seq = 0

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        return None

    def _next_id(self) -> str:
        self._seq += 1
        return f"{self._seq}-0"

    async def xadd(
        self,
        name: str,
        fields: dict[str, Any],
        maxlen: Optional[int] = None,
        approximate: bool = True,
        id: str = "*",
    ) -> str:
        entries = self._streams.setdefault(name, [])
        entry_id = self._next_id() if id == "*" else id
        entries.append((entry_id, dict(fields)))
        if maxlen is not None and len(entries) > maxlen:
            del entries[: len(entries) - maxlen]
        return entry_id

    async def xtrim(
        self, name: str, maxlen: Optional[int] = None, approximate: bool = True
    ) -> int:
        entries = self._streams.get(name, [])
        if maxlen is None or len(entries) <= maxlen:
            return 0
        trimmed = len(entries) - maxlen
        del entries[:trimmed]
        return trimmed

    async def xlen(self, name: str) -> int:
        return len(self._streams.get(name, []))

    async def xrange(
        self, name: str, min: str = "-", max: str = "+", count: Optional[int] = None
    ) -> list[tuple[str, dict[str, Any]]]:
        entries = self._streams.get(name, [])
        return list(entries[:count]) if count is not None else list(entries)


@pytest.fixture
def fake_redis() -> FakeAsyncRedis:
    """A fresh in-memory fake Redis for each test."""
    return FakeAsyncRedis()


@pytest.fixture
def stream_pipeline_module():
    """The stream_pipeline module under test, for constructing extra instances."""
    return stream_pipeline


@pytest_asyncio.fixture
async def pipeline(fake_redis: FakeAsyncRedis):
    """A StreamPipeline wired to the in-memory fake, pre-connected.

    Bypasses `connect()` (which requires a real Redis TCP handshake) by
    injecting the fake directly and marking the pipeline connected, the
    same shape every stream_pipeline test needs.
    """
    p = stream_pipeline.StreamPipeline(redis_url="redis://fake", enabled=True)
    p._redis = fake_redis
    p._connected = True
    return p
