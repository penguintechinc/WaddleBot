"""svc-action -- Quart application entrypoint.

ACTION stage-runner (docs/plans/2026-08-31-app-bundle-sdk-design.md Sec6):
dequeues `waddles:t:{tenant}:c:{community}:app:{app_id}:action` (Valkey,
BRPOP fan-in -- services/runner.py) and dispatches each item to its
bundle's declared `action_target` via one of the five standardized
adapters (services/adapters/). The HTTP surface here is intentionally
thin -- only `/health` (k8s liveness/readiness, same as every other
pipeline-stage container) -- the real work happens in the background
runner task started in `before_serving`.
"""

from __future__ import annotations

from flask_core import create_health_blueprint, setup_aaa_logging
from quart import Quart

from config import ActionConfig
from services.runner import ActionRunner

app = Quart(__name__)

_config = ActionConfig.from_env()

health_bp = create_health_blueprint(_config.module_name, _config.module_version)
app.register_blueprint(health_bp)

logger = setup_aaa_logging(_config.module_name, _config.module_version)

app.config["ACTION_CONFIG"] = _config
_runner = ActionRunner(_config)
app.config["ACTION_RUNNER"] = _runner


@app.before_serving
async def _start_runner() -> None:
    """Open Valkey/DB connections and start the BRPOP dispatch loop."""
    await _runner.start()


@app.after_serving
async def _stop_runner() -> None:
    """Stop the dispatch loop and close all connections cleanly."""
    await _runner.stop()


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import asyncio

    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{_config.module_port}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
