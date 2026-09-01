"""Reverse-proxy client for `loyalty-interaction` -- port of `loyaltyController.js`.

Unlike the polls/forms proxy (`community_engagement_proxy.py`, which
forwards the caller's own bearer token), Node's `loyaltyController.js`
authenticates to the downstream `loyalty-interaction` service with a
shared **service** credential (`config.serviceApiKey` -> `X-API-Key`
header) -- this is service-to-service auth, not user auth passthrough.
Ported here as `SERVICE_API_KEY` (the same env var this port's internal
ingestion endpoints already read, `community_common.is_valid_service_key`)
sent as `X-API-Key`, matching Node's header name exactly.

`proxy_get_or_default` mirrors Node's graceful-degradation behavior: if
`loyalty-interaction` is unreachable (e.g. not deployed in beta), every
read endpoint returns `{success: True, unavailable: True, **defaults}`
rather than a 5xx -- the frontend always gets the expected shape.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

_LOYALTY_URL = os.getenv("LOYALTY_API_URL", "http://loyalty-interaction:8032")
_TIMEOUT_SECONDS = 10.0

DEFAULT_LOYALTY_CONFIG: dict[str, Any] = {
    "currency_name": "Points",
    "currency_symbol": "$",
    "currency_emoji": "\U0001fa99",
    "chat_enabled": False,
    "chat_rate": 0.5,
    "chat_cooldown": 30,
    "follow_enabled": False,
    "follow_rate": 100,
    "subscription_enabled": False,
    "subscription_rate": 500,
    "subscription_t2_multiplier": 2.0,
    "subscription_t3_multiplier": 3.0,
    "gift_subscription_enabled": False,
    "gift_rate": 300,
    "raid_enabled": False,
    "raid_rate": 200,
    "cheer_enabled": False,
    "cheer_per_100bits": 100,
    "donation_enabled": False,
    "donation_per_dollar": 100,
    "gambling_enabled": False,
    "min_bet": 10,
    "max_bet": 10000,
    "slots_enabled": False,
    "coinflip_enabled": False,
    "roulette_enabled": False,
    "duels_enabled": False,
    "min_wager": 10,
    "max_wager": 5000,
    "duel_timeout": 5,
    "gear_enabled": False,
    "gear_drops_enabled": False,
}


async def _proxy(
    method: str, path: str, *, json_body: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Forward a request to `loyalty-interaction`; connection failure degrades to `unavailable`."""
    headers = {"Content-Type": "application/json", "X-API-Key": os.getenv("SERVICE_API_KEY", "")}
    async with httpx.AsyncClient(base_url=_LOYALTY_URL, timeout=_TIMEOUT_SECONDS) as client:
        try:
            resp = await client.request(method, path, json=json_body, headers=headers)
        except httpx.RequestError:
            return {"success": True, "unavailable": True, "message": "Loyalty module not available"}

    try:
        data: dict[str, Any] = resp.json()
    except ValueError:
        data = {}
    if resp.status_code >= 400:
        message = data.get("error") or data.get("message") or "Loyalty module request failed"
        raise LoyaltyProxyError(str(message))
    return data


class LoyaltyProxyError(Exception):
    """Raised when `loyalty-interaction` responds with a non-2xx status."""


async def get_or_default(path: str, defaults: dict[str, Any]) -> dict[str, Any]:
    """GET `path`; merge `defaults` into the response if the service is unavailable."""
    data = await _proxy("GET", path)
    if data.get("unavailable"):
        return {"success": True, "unavailable": True, **defaults}
    return data


async def call(method: str, path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Forward a write (POST/PUT/DELETE) request as-is."""
    return await _proxy(method, path, json_body=json_body)
