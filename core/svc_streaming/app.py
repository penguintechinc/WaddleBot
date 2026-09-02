"""svc-streaming -- Quart application factory + hypercorn entry point.

The 8th container / Streaming module's control plane + real ffmpeg data
plane (`docs/plans/2026-08-31-svc-streaming-design.md`). Follows the same
`create_app()`/blueprint-auto-discovery shape `core/svc_presentation/
app.py` established for this monorepo's newer first-party Quart services
(itself following `hub_api/app.py`'s own precedent).

Real Quart serving, a real pydal-backed control plane (`services/
schema.py`, `services/streaming_service.py`), and a real `ffmpeg`
subprocess data plane (`services/ffmpeg_engine.py`) doing the actual
HLS/RTMP ingest + fan-out-to-N-targets forwarding -- not simulated. This
is a deliberate, documented scope choice: the design spec targets a
first-party Rust media engine or a control plane fronting external
MarchProxy/LiveKit (§1, §8.1, both still genuinely open per that spec);
this build is Python/Quart control-plane + orchestration with `ffmpeg`
(the real, external, industry-standard media engine) as the data plane,
because neither MarchProxy nor LiveKit exists in this repo/environment to
front for tonight's alpha demo. See this PR's description for the full
rationale; the Rust data-plane migration remains a documented follow-up.

The word "restream" is never used anywhere in this file or its docs --
"forward" / "stream-forwarding" / "forward to targets" only (design spec
Terminology, mandatory; trademark caution).
"""

from __future__ import annotations

import asyncio

from flask_core import create_health_blueprint, init_database, install_rate_limiting, setup_aaa_logging
from quart import Quart
from quart_schema import QuartSchema

from blueprints import register_blueprints
from config import Config
from openapi.routes import register_openapi_docs
from services.ffmpeg_engine import FFmpegSupervisor
from services.schema import bind_shared_read_tables, bind_streaming_tables


def create_app(config: Config | None = None) -> Quart:
    """Build the svc-streaming Quart application."""
    cfg = config or Config.from_env()
    app = Quart(__name__)
    app.config["APP_CONFIG"] = cfg

    # Public/full OpenAPI docs mounted at /openapi/v1-public.json and
    # /openapi/v1.json (own auth chain, see openapi/routes.py) -- the
    # DEFAULT quart-schema doc/UI routes are disabled (openapi_path=None,
    # swagger_ui_path=None) so this service never accidentally serves an
    # unauthenticated full-surface spec at the well-known path
    # (backend.md OpenAPI: "the default-mounted UI/spec route... is fully
    # unauthenticated and covers every endpoint").
    QuartSchema(app, openapi_path=None, swagger_ui_path=None, redoc_ui_path=None)

    logger = setup_aaa_logging(cfg.module_name, cfg.module_version, log_level=cfg.log_level)
    app.config["logger"] = logger

    app.register_blueprint(create_health_blueprint(cfg.module_name, cfg.module_version))
    register_blueprints(app)
    register_openapi_docs(app)

    # SECURITY (A04): every stream-control route had zero rate limiting --
    # shared global before_request hook, see flask_core.http_rate_limit
    # module docstring.
    install_rate_limiting(app, namespace=cfg.module_name, redis_url=cfg.valkey_url)

    app.config["FFMPEG_SUPERVISOR"] = FFmpegSupervisor()

    @app.before_serving
    async def startup() -> None:
        """Initialize the DAL, bind this service's own + shared read-only tables."""
        logger.system("Starting svc-streaming", action="startup", extra={"port": cfg.module_port})

        async_dal = init_database(cfg.database_url, pool_size=cfg.db_pool_size)
        dal = async_dal.dal
        bind_streaming_tables(dal, migrate=cfg.db_migrate)
        bind_shared_read_tables(dal, migrate=cfg.db_migrate)
        # `lazy_tables=True` (AsyncDAL's own default) defers each table's
        # actual `CREATE TABLE` until first ORM access -- left lazy, the
        # first access could happen on an `async_dal.*_async()` worker
        # thread mid-request, racing its own `CREATE TABLE` against this
        # thread's still-open sqlite file handle (same gotcha `core/
        # svc_presentation/app.py`'s own startup hook documents). Touching
        # every table once here, still on this thread, forces that DDL to
        # run before any worker thread exists.
        for table_name in dal.tables:
            dal(dal[table_name]).count()
        app.config["async_dal"] = async_dal
        app.config["dal"] = dal

        logger.system("svc-streaming started", action="startup", result="SUCCESS")

    @app.after_serving
    async def shutdown() -> None:
        """Stop every supervised ffmpeg job, then close the DAL connection pool."""
        supervisor: FFmpegSupervisor = app.config["FFMPEG_SUPERVISOR"]
        await supervisor.stop_all()

        async_dal = app.config.get("async_dal")
        if async_dal is not None:
            try:
                await async_dal.close_async()
            except Exception as exc:  # noqa: BLE001 - shutdown must not raise
                logger.warning(f"Error closing DAL on shutdown: {exc}")
        logger.system("svc-streaming shutdown complete", action="shutdown", result="SUCCESS")

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover - process entrypoint, not exercised by unit tests
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{app.config['APP_CONFIG'].module_port}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
