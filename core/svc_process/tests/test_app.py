"""Smoke tests for svc-process's Quart app -- mirrors `core/svc_ingest/tests/test_app.py`."""

from __future__ import annotations

from typing import Any

import pytest
from flask_core import get_bundle_dal, reset_bundle_dal_for_tests

from app import app as quart_app


@pytest.fixture
def client() -> Any:
    return quart_app.test_client()


@pytest.fixture(autouse=True)
def _reset_bundle_dal() -> Any:
    """`set_bundle_dal()` binds a process-wide singleton -- never leak it across test modules."""
    yield
    reset_bundle_dal_for_tests()


class TestHealthEndpoints:
    async def test_health(self, client: Any) -> None:
        async with client as c:
            response = await c.get("/health")
            assert response.status_code == 200
            body = await response.get_json()
            assert body["module"] == "svc-process"

    async def test_healthz(self, client: Any) -> None:
        async with client as c:
            response = await c.get("/healthz")
            assert response.status_code == 200

    async def test_metrics(self, client: Any) -> None:
        async with client as c:
            response = await c.get("/metrics")
            assert response.status_code == 200


class TestLifespan:
    async def test_startup_wires_runner_and_shutdown_stops_it_cleanly(self) -> None:
        """`app.test_app()` (not `test_client()`) is Quart's lifespan-triggering context manager."""
        async with quart_app.test_app() as test_app:
            client = test_app.test_client()
            response = await client.get("/health")
            assert response.status_code == 200
            assert quart_app.config["runner"] is not None
            assert not quart_app.config["runner_task"].done()
        assert quart_app.config["runner_task"].done()

    async def test_startup_binds_dal_for_get_bundle_dal(self) -> None:
        """`startup()` calls `set_bundle_dal()`.

        A stateful process bundle's `get_bundle_dal()` must resolve to the
        exact same `AsyncDAL` instance `app.config["async_dal"]` holds.
        """
        async with quart_app.test_app():
            assert quart_app.config["async_dal"] is not None
            assert get_bundle_dal() is quart_app.config["async_dal"]
