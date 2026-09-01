"""Smoke tests for svc-process's Quart app -- mirrors `core/svc_ingest/tests/test_app.py`."""

from __future__ import annotations

from typing import Any

import pytest

from app import app as quart_app


@pytest.fixture
def client() -> Any:
    return quart_app.test_client()


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
