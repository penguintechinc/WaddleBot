"""Credential Manager - Main application entry point.

Quart async web application that provides:
- Health check endpoint
- Background token refresh polling
- Credential status monitoring
- Force refresh capability
- Redis pub/sub notification on credential changes
"""

from __future__ import annotations

import asyncio
import logging
import sys

from quart import Quart, jsonify

from .config import Config
from .services.refresh_service import RefreshService

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Quart(__name__)
refresh_service: RefreshService | None = None
_shutdown_event = asyncio.Event()


@app.before_serving
async def startup() -> None:
    """Initialize the refresh service and start polling."""
    global refresh_service

    errors = Config.validate()
    if errors:
        logger.error("Configuration errors: %s", errors)
        sys.exit(1)

    refresh_service = RefreshService(
        database_url=Config.DATABASE_URL,
        redis_url=Config.REDIS_URL,
        redis_prefix=Config.REDIS_KEY_PREFIX,
        refresh_buffer=Config.TOKEN_REFRESH_BUFFER,
        poll_interval=Config.POLL_INTERVAL,
        max_retries=Config.MAX_REFRESH_RETRIES,
        retry_backoff_base=Config.RETRY_BACKOFF_BASE,
    )
    await refresh_service.start()
    logger.info(
        "Credential Manager started (poll=%ds, buffer=%ds)",
        Config.POLL_INTERVAL,
        Config.TOKEN_REFRESH_BUFFER,
    )


@app.after_serving
async def shutdown() -> None:
    """Stop the refresh service gracefully."""
    if refresh_service:
        await refresh_service.stop()
    logger.info("Credential Manager stopped")


@app.route("/health")
async def health() -> tuple:
    """Health check endpoint."""
    status = "healthy"
    details = {
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
    }

    if refresh_service:
        svc_status = refresh_service.get_status()
        details.update(svc_status)
        if not svc_status.get("running"):
            status = "degraded"

    code = 200 if status == "healthy" else 503
    return jsonify({"status": status, **details}), code


@app.route("/api/v1/credentials/status")
async def credential_status() -> tuple:
    """Return status of all tracked platform integrations."""
    if not refresh_service:
        return jsonify({"error": "Service not initialized"}), 503

    stats = await refresh_service.get_credential_stats()
    return jsonify({"success": True, "stats": stats}), 200


@app.route("/api/v1/credentials/refresh-now", methods=["POST"])
async def force_refresh() -> tuple:
    """Force an immediate credential refresh cycle."""
    if not refresh_service:
        return jsonify({"error": "Service not initialized"}), 503

    count = await refresh_service.run_refresh_cycle()
    return jsonify({
        "success": True,
        "message": f"Refreshed {count} credentials",
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.MODULE_PORT)
