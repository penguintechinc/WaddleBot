"""Shared fixtures for svc-ingest's own tests.

`redis_client` is a real `fakeredis.FakeAsyncRedis` -- genuine LPUSH/RPOP/
LIST semantics executed in-memory (not a mock of the call), the "fakeredis
... real key round-trip" option this PR's own task spec calls out.
"""

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
