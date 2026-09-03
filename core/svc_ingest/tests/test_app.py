"""Smoke tests for svc-ingest's Quart app -- health endpoints + real startup/shutdown lifecycle.

`app.test_client()`'s own `async with` does NOT run the ASGI lifespan
(confirmed via `QuartClient.__aenter__` source -- it only sets
`preserve_context`); `app.test_app()` is Quart's actual lifespan-triggering
context manager (`before_serving`/`after_serving` run on enter/exit) and is
what `TestLifespan` below uses. `VALKEY_URL` defaults to
`redis://localhost:6379/0` (config.py) -- `redis.from_url()` itself never
opens a socket until the first command, so startup succeeds without a live
Valkey; the background `run_forever()` task's first `poll_once()` fails
closed (httpx connection refused to the default `hub-api:8204`) and
degrades to an empty bundle set, exactly the graceful-degrade contract
`BundlePoller` guarantees -- proven separately, with a real fakeredis round
trip, by `test_runner.py`.
"""

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
            assert body["module"] == "svc-ingest"

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
        """The real `@app.before_serving`/`@app.after_serving` hooks run without raising.

        Proves the background task actually starts (config populated,
        `runner_task` present) and that `stop()` + task cancellation on
        shutdown terminates cleanly -- no hang, no unhandled exception.
        """
        async with quart_app.test_app() as test_app:
            client = test_app.test_client()
            response = await client.get("/health")
            assert response.status_code == 200
            assert quart_app.config["runner"] is not None
            assert not quart_app.config["runner_task"].done()
        # test_app's __aexit__ runs the ASGI lifespan shutdown, which calls
        # our after_serving hook -- by the time this block exits, the
        # runner task must be finished (stopped, not hung).
        assert quart_app.config["runner_task"].done()

    async def test_startup_wires_supervisor_with_no_receivers_when_no_token(self) -> None:
        """No `DISCORD_BOT_TOKEN` -- the supervisor still starts, with zero receivers.

        `discord_leased_receiver` is never populated (graceful skip,
        matching `trigger/receiver/discord_module/app.py`'s own
        precedent) -- test env has no token set by default.
        """
        async with quart_app.test_app():
            assert quart_app.config["supervisor"] is not None
            assert quart_app.config["registry"] is not None
            assert "discord_leased_receiver" not in quart_app.config
