"""The Twitch chat + EventSub ingest bundles' manifests.

Registered into svc-ingest's own in-process `flask_core.app_registry.
AppRegistry` at startup (`app.py`), separate from -- and NOT loaded via --
hub-api's distribution HTTP endpoint the way the poll-drain loop
(`runner.py`) loads its bundles. Mirrors `bundles/discord_gateway_
manifest.py`'s own precedent -- see that module's docstring for why
`is_default=True` + no real `InstallationLookup` wiring is a deliberate,
documented MVP scope choice.

Two Apps registered, under two DIFFERENT Features -- `flask_core.
app_manifest`'s `_FEATURE_RE`/`_APP_ID_RE` require `feature` to be exactly
`waddles.<module>.<feature>` (3 segments) and `app_id`'s own first three
segments to equal it, so a `feature` value cannot itself contain a
further `.`-separated qualifier the way an earlier draft of this module
tried (`waddles.bot.twitch.chat` is a valid 4-segment *app_id* shape, not
a valid 3-segment *feature* shape):

- `waddles.bot.twitch.gateway` -- the IRC chat receiver
  (`receivers/twitch_irc.py`), feature `waddles.bot.twitch` (matches
  Discord's own `waddles.bot.discord` gateway-bundle convention exactly),
  platform-level, `communication_model="gateway_socket"`.
- `waddles.bot.twitchevents.eventsub` -- the EventSub webhook handler
  (`eventsub.py`), feature `waddles.bot.twitchevents` (a single token,
  deliberately NOT `waddles.bot.twitch` -- `AppRegistry.register` rejects
  a second `is_default=True` App per feature, and this bundle needs to be
  its own feature's default so `fanout.resolve_consuming_apps`'s
  `resolve_apps` fallback finds IT, not the chat gateway, when no
  `InstallationLookup` row exists yet), `communication_model=
  "webhook_push"` (the existing StageSpec value for a thirdparty-push-fed
  stage -- EventSub genuinely IS a webhook Twitch calls into this
  service, unlike the IRC socket the chat gateway holds).
"""

from __future__ import annotations

from typing import Any

from flask_core.app_manifest import AppManifest
from flask_core.app_registry import AppRegistry

#: Raw manifest dict -- validated + parsed via `flask_core.app_manifest.
#: parse_manifest` at registration time, never constructed as an
#: `AppManifest` directly (see that module's own docstring on why).
TWITCH_GATEWAY_MANIFEST: dict[str, Any] = {
    "app_id": "waddles.bot.twitch.gateway",
    "name": "Twitch Chat Ingest",
    "version": "1.0.0",
    "feature": "waddles.bot.twitch",
    "module": "bot",
    "provider": "builtin",
    "is_default": True,
    "stages": {
        "ingest": {
            # Run by the poll-drain loop (runner.py), NOT the IRC
            # receiver directly -- the receiver only fans the raw event
            # out onto this bundle's `:ingest` Valkey key
            # (`bundle_stream_key`); `runner.py`'s own poll loop RPOPs it
            # and calls this entrypoint exactly like every other ingest
            # bundle.
            "entrypoint": "bundles.twitch_ingest:normalize",
            "consumes": ["twitch.message"],
            "communication_model": "gateway_socket",
        }
    },
}

TWITCH_EVENTSUB_MANIFEST: dict[str, Any] = {
    "app_id": "waddles.bot.twitchevents.eventsub",
    "name": "Twitch EventSub Ingest",
    "version": "1.0.0",
    "feature": "waddles.bot.twitchevents",
    "module": "bot",
    "provider": "builtin",
    "is_default": True,
    "stages": {
        "ingest": {
            "entrypoint": "bundles.twitch_eventsub_ingest:normalize",
            "consumes": ["twitch.eventsub"],
            "communication_model": "webhook_push",
        }
    },
}


def register_default_bundles(registry: AppRegistry) -> tuple[AppManifest, AppManifest]:
    """Load + register both Twitch manifests into `registry`. Returns `(gateway, eventsub)`."""
    gateway = registry.load(TWITCH_GATEWAY_MANIFEST)
    eventsub = registry.load(TWITCH_EVENTSUB_MANIFEST)
    return gateway, eventsub
