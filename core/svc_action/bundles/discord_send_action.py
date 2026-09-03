"""Discord send-message ACTION bundle -- real Discord Bot API `POST .../messages` call.

Ported from `action/pushing/discord_action_module/services/
discord_service.py`'s `send_message` (the legacy module's real Discord API
logic -- Bot-token auth, Create Message endpoint, 429/`Retry-After`
handling) into the App Bundle SDK's action-stage script contract:
`async def <name>(envelope, config, *, http_client) -> AdapterResult`
(`services/adapters/bundle.py`).

Reuses this stage-runner's existing SSRF guard (`services.url_guard.
guarded_request`) and secret resolution (`services.signing.resolve_secret`
-- an env-var-name indirection, never a raw bot token in `app_catalog`/
`app_activations` config) rather than reimplementing either. Deliberately
does **not** port `discord_service.py`'s own `asyncio.sleep`-based 429
retry loop, per-endpoint rate-limit dict, or its `discord_actions` audit
table -- all three are now handled by svc-action's platform-level
`retry_with_backoff` (`RetryableDispatchError` on 429/5xx,
`services/runner.py::_dispatch_with_retry`) and `action_dispatch_log`
respectively, so this bundle stays a thin, stateless script instead of
duplicating retry/audit infrastructure the platform already provides.
Seeded via `config/postgres/migrations/082_discord_send_action_bundle.sql`
as `waddles.bot.discord.default`'s `stages.action.entrypoint`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope
from services.signing import SecretResolutionError, resolve_secret
from services.url_guard import SSRFError, guarded_request

#: Real Discord REST API base -- overridable via bundle `config["api_base"]`
#: (tests point this at a literal-IP mock target, matching every other
#: adapter's test convention of avoiding real DNS resolution in unit tests
#: -- `services/url_guard.py`'s `validate_url` resolves the host via
#: `socket.getaddrinfo` before every request, including in tests).
_DEFAULT_API_BASE = "https://discord.com/api/v10"


async def send_message(
    envelope: ActionEnvelope,
    config: Mapping[str, Any],
    *,
    http_client: httpx.AsyncClient,
) -> AdapterResult:
    """Send `envelope.payload["text"]` to a Discord channel via the Bot API.

    `config` is the bundle's resolved `stages.action.config` (the catalog's
    own defaults merged with any activation-level override --
    `services/config_lookup.py::get_action_entrypoint`) and must declare
    `channel_id` and `bot_token_ref` (an env-var *name*, resolved via
    `resolve_secret` -- never a literal token in DB config). `api_base`
    optionally overrides the Discord API root (default: the real Discord
    API).

    Raises `NonRetryableDispatchError` for a config/auth failure (missing
    config field, unresolvable secret, 401/403, any other 4xx) and
    `RetryableDispatchError` for a 429 (rate limited -- `retry_with_backoff`
    in `runner.py` owns the actual backoff; this bundle never sleeps
    itself) or a 5xx/network error.
    """
    channel_id = config.get("channel_id")
    if not isinstance(channel_id, str) or not channel_id:
        raise NonRetryableDispatchError("discord bundle config missing required 'channel_id'")

    bot_token_ref = config.get("bot_token_ref")
    if not isinstance(bot_token_ref, str) or not bot_token_ref:
        raise NonRetryableDispatchError("discord bundle config missing required 'bot_token_ref'")

    text = envelope.payload.get("text")
    if not isinstance(text, str) or not text:
        raise NonRetryableDispatchError("action envelope payload missing required 'text' string")

    try:
        bot_token = resolve_secret(bot_token_ref)
    except SecretResolutionError as exc:
        raise NonRetryableDispatchError(f"discord bot token resolution failed: {exc}") from exc

    api_base = config.get("api_base", _DEFAULT_API_BASE)
    url = f"{api_base}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {"content": text}
    embed = envelope.payload.get("embed")
    if isinstance(embed, dict):
        body["embeds"] = [embed]

    try:
        response = await guarded_request(http_client, "POST", url, headers=headers, json=body)
    except SSRFError as exc:
        raise NonRetryableDispatchError(f"discord API URL rejected by SSRF guard: {exc}") from exc
    except (httpx.TimeoutException, httpx.NetworkError, httpx.TransportError) as exc:
        raise RetryableDispatchError(f"discord API request failed: {exc}") from exc

    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After", "1")
        raise RetryableDispatchError(
            f"discord API rate limited, retry after {retry_after}s", http_status=429
        )
    if response.status_code in (401, 403):
        raise NonRetryableDispatchError(
            f"discord API rejected auth: HTTP {response.status_code}",
            http_status=response.status_code,
        )
    if 400 <= response.status_code < 500:
        raise NonRetryableDispatchError(
            f"discord API returned client error: HTTP {response.status_code} {response.text[:200]}",
            http_status=response.status_code,
        )
    if response.status_code >= 500:
        raise RetryableDispatchError(
            f"discord API returned server error: HTTP {response.status_code}",
            http_status=response.status_code,
        )

    message_id = None
    try:
        message_id = response.json().get("id")
    except Exception:  # noqa: BLE001, S110 -- best-effort audit detail only, never fatal
        pass

    return AdapterResult(
        target_type="bundle",
        detail=f"discord message sent, channel={channel_id} message_id={message_id}",
        http_status=response.status_code,
    )
