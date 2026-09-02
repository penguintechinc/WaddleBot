"""
Translate Interaction Module - Main Application

Dual-interface translation microservice:
- gRPC (port 50033): hot-path calls from router
- REST (port 8033):  health checks, cache admin, language detect
"""
import asyncio
import logging
import logging.handlers
import os
import sys
import time
from collections import OrderedDict
from concurrent import futures

import grpc
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from pydal import DAL
from quart import Quart, jsonify, request

from config import Config
from proto import translate_interaction_pb2_grpc
from services.grpc_handler import TranslateInteractionServicer
from grpc_tls import bind_secure_port, default_server_options
from services.translation_service import TranslationService

# Logging setup — create log dir if needed
os.makedirs(Config.LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="[%(asctime)s] %(levelname)s %(name)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            f"{Config.LOG_DIR}/{Config.MODULE_NAME}.log",
            maxBytes=10485760,
            backupCount=5,
        ),
    ],
)
logger = logging.getLogger(__name__)

# Quart REST app
app = Quart(__name__)

# Global service instances
dal = None
translation_service = None


# ---------------------------------------------------------------------------
# Cache manager
# ---------------------------------------------------------------------------

class _CacheManager:
    """Simple in-memory LRU + Redis cache manager."""

    def __init__(self):
        self._memory: OrderedDict = OrderedDict()
        self._max = 1000
        self._redis = None

    async def _get_redis(self):
        if self._redis is None and Config.REDIS_URL:
            import aioredis
            self._redis = await aioredis.from_url(Config.REDIS_URL)
        return self._redis

    async def get(self, key: str):
        if key in self._memory:
            val, expires = self._memory[key]
            if expires > time.time():
                self._memory.move_to_end(key)
                return val
            del self._memory[key]
        r = await self._get_redis()
        if r:
            val = await r.get(key)
            if val:
                return val.decode() if isinstance(val, bytes) else val
        return None

    async def set(self, key: str, value, ttl: int = 3600):
        if len(self._memory) >= self._max:
            self._memory.popitem(last=False)
        self._memory[key] = (value, time.time() + ttl)
        r = await self._get_redis()
        if r:
            await r.set(key, value, ex=ttl)

    async def delete(self, key: str):
        self._memory.pop(key, None)
        r = await self._get_redis()
        if r:
            await r.delete(key)


cache_manager = _CacheManager()


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@app.before_serving
async def startup():
    global dal, translation_service
    dal = DAL(Config.DATABASE_URL, folder=None, pool_size=10)
    translation_service = TranslationService(dal=dal, cache_manager=cache_manager)
    logger.info(
        f"{Config.MODULE_NAME} v{Config.MODULE_VERSION} "
        f"REST:{Config.MODULE_PORT} gRPC:{Config.GRPC_PORT}"
    )


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
async def health():
    return jsonify({
        "status": "healthy",
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
        "rest_port": Config.MODULE_PORT,
        "grpc_port": Config.GRPC_PORT,
    })


@app.route("/api/v1/translate", methods=["POST"])
async def translate():
    """REST translation endpoint (for non-router callers)."""
    data = await request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    text = data.get('text', '').strip()
    target_lang = data.get('target_lang', 'en')
    community_id = data.get('community_id')
    platform = data.get('platform', 'unknown')
    channel_id = data.get('channel_id', '')
    if not text:
        return jsonify({"error": "text is required"}), 400
    if not community_id:
        return jsonify({"error": "community_id is required"}), 400
    try:
        handler = TranslateInteractionServicer(translation_service, dal)
        config = await handler._load_config(community_id)
        result = await translation_service.translate(
            text=text, target_lang=target_lang,
            community_id=community_id, config=config,
            platform=platform, channel_id=channel_id,
        )
        if result is None:
            return jsonify({"skipped": True, "reason": "translation not needed"})
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        logger.error(f"REST translate error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/translate/detect", methods=["POST"])
async def detect():
    data = await request.get_json()
    if not data or not data.get('text', '').strip():
        return jsonify({"error": "text is required"}), 400
    try:
        lang, conf = await translation_service._detect_language(data['text'])
        return jsonify({"detected_lang": lang, "confidence": conf})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/translate/cache/stats", methods=["GET"])
async def cache_stats():
    try:
        stats = await translation_service.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/translate/cache/cleanup", methods=["POST"])
async def cache_cleanup():
    try:
        await translation_service.cleanup_cache()
        return jsonify({"message": "Cache cleanup complete"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# gRPC server
# ---------------------------------------------------------------------------

async def start_grpc_server():
    """Run gRPC server (called concurrently with Quart)."""
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=Config.GRPC_MAX_WORKERS),
        options=default_server_options(),
    )
    translate_interaction_pb2_grpc.add_TranslateInteractionServicer_to_server(
        TranslateInteractionServicer(translation_service, dal),
        server,
    )
    bind_secure_port(server, f"{Config.HOST}:{Config.GRPC_PORT}")
    await server.start()
    logger.info(f"gRPC server (TLS) listening on port {Config.GRPC_PORT}")
    await server.wait_for_termination()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main():
    hconfig = HypercornConfig()
    hconfig.bind = [f"{Config.HOST}:{Config.MODULE_PORT}"]

    grpc_task = asyncio.create_task(start_grpc_server())
    rest_task = asyncio.create_task(serve(app, hconfig))

    await asyncio.gather(grpc_task, rest_task)


if __name__ == "__main__":
    asyncio.run(main())
