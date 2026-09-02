"""Global sliding-window rate limiting -- security.md A04 hardening.

hub-api had `RATE_LIMIT_MAX_REQUESTS`/`RATE_LIMIT_WINDOW_MS` wired into
every environment's Helm/kustomize env (`values-beta.yaml`, alpha/beta
`kustomization.yaml` overlays) but no code anywhere read them -- all 449
endpoints were unlimited. This module is the fix: a single Quart
`before_request` hook, registered once in `app.py::create_app()`, in
front of every route -- not a per-route decorator, which would need 449
individual call sites and would silently miss the 450th.

Reuses `flask_core.rate_limiter.RateLimiter` (Redis sliding-window,
already the shared implementation `core/ai_researcher_module` and
`flask_core.api_utils.rate_limit`'s own per-route decorator build on) --
not reimplemented here. Two tiers:

- **auth**: login/token/passkey -- the brute-force-sensitive surface,
  `HubAPIConfig.rate_limit_auth_max_requests`/`rate_limit_auth_window_seconds`.
- **standard**: everything else, `HubAPIConfig.rate_limit_max_requests`/
  `rate_limit_window_seconds`.

Identifier is per-authenticated-user (`sub` claim) when a valid bearer
token is present, else per-client-IP -- crucially IP-based for the
pre-auth `POST /api/v1/auth/login` itself, which is exactly the
brute-force surface this needs to bound. Health probes (`/health`,
`/healthz`) are exempt so K8s liveness/readiness never 429s.
"""

from __future__ import annotations

from flask_core.api_utils import error_response
from flask_core.rate_limiter import RateLimiter
from quart import Quart, request

from config import HubAPIConfig
from services.current_user import get_optional_current_user_id

#: Path prefixes routed to the stricter auth tier -- prefix match on
#: `request.path`, not exact, so it covers every route
#: `blueprints/v1/auth.py` (login/register/refresh/passkey-login/oauth
#: exchange/temp-password) and `blueprints/v1/passkey.py`
#: (registration ceremonies) register, present and future, without
#: needing a per-route opt-in.
_AUTH_TIER_PREFIXES: tuple[str, ...] = (
    "/api/v1/auth/",
    "/api/v1/user/passkey/",
)

#: K8s liveness/readiness probes -- never rate limited, or a busy cluster
#: starts killing healthy pods for the wrong reason.
_EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/healthz"})

#: `app.config` key the installed `RateLimiter` instance is stored under,
#: so `app.py`'s `before_serving`/`after_serving` hooks can `connect()`/
#: `disconnect()` its Redis connection as part of the ASGI lifespan.
RATE_LIMITER_CONFIG_KEY = "rate_limiter"


def _client_ip() -> str:
    """Best-effort client IP: first `X-Forwarded-For` hop, else the ASGI peer addr."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _rate_limit_identifier() -> str:
    """Per-user identifier when authenticated, else per-IP.

    A valid bearer token buckets by `sub` (id) so one legitimate user
    isn't starved by noisy neighbors sharing a NAT/proxy IP; anything
    unauthenticated -- including a failed/absent token on the login
    endpoint itself -- buckets by IP, which is the actual brute-force
    surface this tier exists to bound.
    """
    user_id = get_optional_current_user_id(request)
    if user_id is not None:
        return f"user:{user_id}"
    return f"ip:{_client_ip()}"


def _is_auth_tier(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _AUTH_TIER_PREFIXES)


def install_rate_limiting(app: Quart, cfg: HubAPIConfig) -> RateLimiter:
    """Wire the global rate-limit `before_request` hook onto `app`.

    Returns the `RateLimiter` instance (also stashed on
    `app.config[RATE_LIMITER_CONFIG_KEY]`) so `app.py` owns the
    connect/disconnect lifecycle against Redis/Valkey rather than this
    module reaching into `before_serving`/`after_serving` itself --
    keeps this module import-safe (no I/O at import time) and testable
    without a running event loop.
    """
    limiter = RateLimiter(redis_url=cfg.valkey_url, namespace="hub_api_rate_limit")
    app.config[RATE_LIMITER_CONFIG_KEY] = limiter

    @app.before_request
    async def _enforce_rate_limit() -> tuple[dict[str, object], int] | None:
        """Reject with 429 once the caller's bucket for this tier is exhausted."""
        path = request.path
        if path in _EXEMPT_PATHS:
            return None

        auth_tier = _is_auth_tier(path)
        if auth_tier:
            limit = cfg.rate_limit_auth_max_requests
            window = cfg.rate_limit_auth_window_seconds
        else:
            limit = cfg.rate_limit_max_requests
            window = cfg.rate_limit_window_seconds

        tier_label = "auth" if auth_tier else "standard"
        # Tier-namespaced so an auth-tier bucket and a standard-tier
        # bucket for the same identifier never share/collide state --
        # a user hammering /api/v1/auth/refresh shouldn't burn down
        # their standard-tier budget for everything else, or vice versa.
        key = f"{tier_label}:{_rate_limit_identifier()}"

        allowed = await limiter.check_rate_limit(key, limit, window)
        if allowed:
            return None

        logger = app.config.get("logger")
        if logger is not None:
            logger.warning(
                f"Rate limit exceeded: {path}",
                action="rate_limit",
                result="BLOCKED",
                extra={"tier": tier_label, "limit": limit, "window_seconds": window},
            )

        response, status_code = error_response(
            "Rate limit exceeded. Please try again later.",
            429,
            "RATE_LIMIT_EXCEEDED",
        )
        response.headers["Retry-After"] = str(window)
        return response, status_code

    return limiter
