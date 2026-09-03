"""svc-action app.py boot test -- health blueprint wiring + lifespan-triggered runner startup."""

from __future__ import annotations

from typing import Any

import pytest


@pytest.fixture
def client() -> Any:
    from app import app as quart_app

    return quart_app.test_client()


class TestHealthEndpoints:
    async def test_health(self, client: Any) -> None:
        """flask_core's health blueprint wiring boots and reports healthy.

        Deliberately does not trigger `before_serving`/`after_serving`
        (which open real Valkey/DB connections and start the poll loop) --
        plain `test_client()` request dispatch never fires them, matching
        core/svc_streaming's own scaffold boot-test pattern. `TestLifespan`
        below covers the lifespan-triggered path.
        """
        response = await client.get("/health")
        assert response.status_code == 200
        data = await response.get_json()
        assert data["status"] == "healthy"
        assert data["module"] == "svc-action"

    async def test_healthz(self, client: Any) -> None:
        response = await client.get("/healthz")
        assert response.status_code == 200

    async def test_metrics(self, client: Any) -> None:
        response = await client.get("/metrics")
        assert response.status_code == 200


class TestLifespan:
    async def test_startup_wires_runner_and_shutdown_stops_it_cleanly(self) -> None:
        """`app.test_app()` (not `test_client()`) is Quart's lifespan-triggering context manager.

        Proves the real `startup()`/`shutdown()` wiring (poller, Valkey
        client, DAL, `ActionRunner`, background `run_forever()` task) boots
        and tears down cleanly -- the distribution poll itself fails
        against no real hub-api (network-unreachable in a test sandbox),
        which `flask_core.stage_runner.BundlePoller.poll_once()` is
        designed to swallow (never raises, degrades to an empty bundle
        set) -- exactly mirrors `core/svc_process/tests/test_app.py`'s own
        lifespan test.
        """
        from app import app as quart_app

        async with quart_app.test_app() as test_app:
            client = test_app.test_client()
            response = await client.get("/health")
            assert response.status_code == 200
            assert quart_app.config["runner"] is not None
            assert not quart_app.config["runner_task"].done()
        assert quart_app.config["runner_task"].done()
