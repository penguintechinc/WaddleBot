"""Shared fixtures for svc-process's own tests -- mirrors `core/svc_ingest/tests/conftest.py`."""

from __future__ import annotations

import os
from typing import Any

import fakeredis
import httpx
import pytest

# Keep `Config`'s DB defaults out of test collection -- mirrors
# `core/svc_action/tests/conftest.py`'s own env defaults exactly. DB_NAME
# "memory" (not the "waddlebot" default) makes `config.py::_build_db_url`'s
# sqlite branch build the true pydal in-memory URI ("sqlite:memory")
# instead of a stray on-disk file. Without this, `TestLifespan` (test_app.py)
# would try a real TCP connection to `infra-postgres:5432` when its lifespan
# triggers `startup()`'s `AsyncDAL(Config.DATABASE_URL, ...)` construction.
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("DB_NAME", "memory")


@pytest.fixture
async def redis_client() -> Any:
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def http_client_factory():
    """Factory: build an `httpx.AsyncClient` wired to a `httpx.MockTransport` handler."""

    def _make(handler: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return _make
