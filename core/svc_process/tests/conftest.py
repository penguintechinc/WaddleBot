"""Shared fixtures for svc-process's own tests -- mirrors `core/svc_ingest/tests/conftest.py`."""

from __future__ import annotations

from typing import Any

import fakeredis
import httpx
import pytest


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
