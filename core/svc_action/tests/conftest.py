"""Pytest bootstrap for svc-action's tests.

svc_action isn't installed as a package (it's a standalone control-plane
directory run via `hypercorn app:app`, same shape as core/svc_streaming/
core/svc_presentation) -- so its own directory has to be put on sys.path
explicitly for `from app import app` / `import config` / `from services...`
to resolve.
"""

from __future__ import annotations

import os
import sys
from typing import Any

import fakeredis
import httpx
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Keep from_env() DB/Valkey defaults out of test collection -- individual
# tests construct their own ActionConfig/AsyncDAL/fakeredis instances
# rather than touching a real network resource at import time. DB_NAME
# "memory" (not the "waddlebot" default) makes ActionConfig.from_env()'s
# sqlite branch build the true pydal in-memory URI ("sqlite:memory") --
# without this, importing `app` (module-level `ActionConfig.from_env()`)
# or a lifespan test would create a stray `waddlebot` sqlite file on disk.
os.environ.setdefault("DB_TYPE", "sqlite")
os.environ.setdefault("DB_NAME", "memory")


@pytest.fixture
async def redis_client() -> Any:
    """Real LIST/PUBLISH semantics via `fakeredis.FakeAsyncRedis` -- mirrors svc-process's own fixture."""
    client = fakeredis.FakeAsyncRedis(decode_responses=True)
    yield client
    await client.aclose()


@pytest.fixture
def http_client_factory() -> Any:
    """Factory: build an `httpx.AsyncClient` wired to a `httpx.MockTransport` handler."""

    def _make(handler: Any) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(handler))

    return _make
