"""Global sliding-window HTTP rate limiting for video_proxy_module -- security.md A04.

Security review: every route in this service had zero rate limiting.
Mirrors the shared fix every other core service now uses
(`flask_core.http_rate_limit.install_rate_limiting`, itself extracted from
hub_api's own gh security PR #255) -- duplicated in a self-contained form
here rather than imported, because `video_proxy_module` ships its own
standalone Dockerfile with no `flask_core` in `requirements.txt` (see
`services/community_authz.py`'s own docstring for the identical
constraint).

A single Quart `before_request` hook, not a per-route decorator -- one call
site in `app.py` covers every route present or future.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from quart import Quart, jsonify, request

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only if redis isn't installed
    REDIS_AVAILABLE = False
    redis = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

#: K8s liveness/readiness probes -- never rate limited.
DEFAULT_EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/healthz"})

#: `app.config` key the installed limiter is stored under.
RATE_LIMITER_CONFIG_KEY = "rate_limiter"


class RateLimiter:
    """Redis-backed sliding-window rate limiter with a REAL in-memory fallback.

    Mirrors `flask_core.rate_limiter.RateLimiter`'s sliding-window
    algorithm (sorted-set based, atomic `zremrangebyscore`/`zcard`/`zadd`)
    and its two-tier degradation -- see that module for the full rationale:

    - Redis/Valkey unreachable at `connect()` time (or the `redis` package
      isn't installed): falls back to an in-memory sliding window that
      still ENFORCES the limit (per-process only, not cluster-wide) --
      not a silent fail-open. This is what makes rate limiting testable
      and meaningfully protective even before Valkey is wired up in a given
      environment.
    - A transient error mid-operation on an otherwise-connected Redis
      client: fails OPEN (allows the request) -- an availability outage in
      the rate limiter must never become an availability outage for the
      service itself.
    """

    def __init__(self, redis_url: str, namespace: str) -> None:
        self.redis_url = redis_url
        self.namespace = namespace
        self._redis: Any = None
        self._connected = False
        self._fallback_enabled = False
        self._fallback_cache: dict[str, list[float]] = {}

    async def connect(self) -> None:
        """Connect to Redis/Valkey (call during startup). Falls back to in-memory, never raises."""
        if not REDIS_AVAILABLE or not self.redis_url:
            logger.warning("Rate limiter: redis unavailable, using in-memory fallback")
            self._fallback_enabled = True
            return
        try:
            self._redis = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True,
                socket_connect_timeout=5, socket_timeout=5,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Rate limiter connected to Redis: %s", self.namespace)
        except Exception as exc:  # noqa: BLE001 -- degrade to in-memory, never block startup
            logger.warning("Rate limiter: Redis connect failed (%s), using in-memory fallback", exc)
            self._fallback_enabled = True

    async def disconnect(self) -> None:
        """Disconnect from Redis (call during shutdown)."""
        if self._redis is not None:
            await self._redis.aclose()
            self._connected = False

    def _key(self, identifier: str) -> str:
        return f"{self.namespace}:{identifier}"

    async def check_rate_limit(self, identifier: str, limit: int, window: int) -> bool:
        """True if the request is allowed; False if the caller's bucket is exhausted."""
        key = self._key(identifier)
        now = time.time()

        if self._fallback_enabled:
            timestamps = [t for t in self._fallback_cache.get(key, []) if t > now - window]
            if len(timestamps) < limit:
                timestamps.append(now)
                self._fallback_cache[key] = timestamps
                return True
            self._fallback_cache[key] = timestamps
            return False

        if not self._connected or self._redis is None:
            return True  # fail open -- connect() was never called at all

        try:
            await self._redis.zremrangebyscore(key, "-inf", now - window)
            count = await self._redis.zcard(key)
            if count < limit:
                await self._redis.zadd(key, {str(now): now})
                await self._redis.expire(key, window)
                return True
            return False
        except Exception as exc:  # noqa: BLE001 -- fail open on a transient Redis error
            logger.warning("Rate limit check failed (%s), failing open", exc)
            return True


def _identifier(payload: dict[str, Any] | None) -> str:
    """Per-authenticated-user identifier when the bearer token verified, else per-IP."""
    if payload is not None:
        user_id = payload.get("sub") or payload.get("user_id")
        if user_id:
            return f"user:{user_id}"
    return f"ip:{request.remote_addr or 'unknown'}"


def install_rate_limiting(
    app: Quart,
    *,
    namespace: str,
    redis_url: str,
    max_requests: int | None = None,
    window_seconds: int | None = None,
    verify_jwt_token: Any,
    jwt_secret_key: str,
    exempt_paths: frozenset[str] = DEFAULT_EXEMPT_PATHS,
) -> RateLimiter:
    """Wire the global rate-limit `before_request` hook onto `app`.

    `verify_jwt_token`/`jwt_secret_key` are passed in (rather than imported)
    so this module stays decoupled from `app.py`'s specific JWT
    implementation -- the caller's own `verify_jwt_token` function.

    `max_requests`/`window_seconds` default to the `RATE_LIMIT_MAX_REQUESTS`/
    `RATE_LIMIT_WINDOW_SECONDS` env vars (matching `flask_core.
    http_rate_limit`'s identical convention), else 120 req/60s.
    """
    max_requests = max_requests or int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"))
    window_seconds = window_seconds or int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    limiter = RateLimiter(redis_url=redis_url, namespace=f"{namespace}_rate_limit")
    app.config[RATE_LIMITER_CONFIG_KEY] = limiter

    @app.before_serving
    async def _connect_rate_limiter() -> None:
        await limiter.connect()

    @app.after_serving
    async def _disconnect_rate_limiter() -> None:
        await limiter.disconnect()

    @app.before_request
    async def _enforce_rate_limit() -> Any:
        if request.path in exempt_paths:
            return None

        payload = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            payload = verify_jwt_token(auth_header[7:])

        key = _identifier(payload)
        allowed = await limiter.check_rate_limit(key, max_requests, window_seconds)
        if allowed:
            return None

        response = jsonify({"error": "Rate limit exceeded. Please try again later."})
        response.status_code = 429
        response.headers["Retry-After"] = str(window_seconds)
        return response

    return limiter
