"""`bundle` action-target adapter -- loads+invokes a real App Bundle script entrypoint.

Unlike the other five adapters (webhook/rest_api/message_queue/overlay/
email), which dispatch to a *generically configured* HTTP/SMTP/Redis
destination, `bundle` dispatches to a *bundle-declared Python script* --
the same `module:function` dotted-path entrypoint convention ingest/
process bundles use (`app_catalog.stages[stage].entrypoint`, migration
071), resolved via `flask_core.stage_runner.load_entrypoint` (importlib,
never `exec()` -- no code-injection surface, see that function's own
docstring). `runner.py::_handle_item` builds this `ActionTarget` only when
the envelope's `app_id` has a catalog-declared `stages.action.entrypoint`
(`services/config_lookup.py::get_action_entrypoint`) -- every other bundle
keeps using the generic adapters above; this module is purely additive.

A bundle script may return either the local `AdapterResult` (e.g.
`discord_send_action.py`) or the shared `waddle_transports.TransportResult`
(e.g. `twitch_send_action.py`, which relays through a `waddle_transports`
transport directly) -- both are accepted here and normalized to
`AdapterResult` before returning, so `runner.py::_record`'s dispatch-log
audit call sees one consistent shape (`target_type`/`detail`/
`http_status`) regardless of which result type the script itself produced.
"""

from __future__ import annotations

import httpx
from flask_core.stage_runner import EntrypointLoadError, load_entrypoint
from waddle_transports import TransportResult

from services.action_target import ActionTarget
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope


async def dispatch(
    target: ActionTarget,
    envelope: ActionEnvelope,
    *,
    http_client: httpx.AsyncClient,
) -> AdapterResult:
    """Load `target.entrypoint` and invoke it as `fn(envelope, config, http_client=...)`.

    The bundle script owns its own retry classification -- it must raise
    `RetryableDispatchError`/`NonRetryableDispatchError` itself (same
    contract every other adapter follows) so `runner.py`'s
    `retry_with_backoff` wrapper treats a bundle-script dispatch exactly
    like a built-in adapter's. Any *other* exception escaping the script
    (an unhandled bug, not a classified failure) is treated as
    non-retryable -- retrying can't fix a bundle bug, only a code change
    can, so this never spins the retry loop on it.
    """
    try:
        entrypoint_fn = load_entrypoint(target.entrypoint)
    except EntrypointLoadError as exc:
        raise NonRetryableDispatchError(f"bundle entrypoint load failed: {exc}") from exc

    try:
        result = await entrypoint_fn(envelope, target.bundle_config, http_client=http_client)
    except (RetryableDispatchError, NonRetryableDispatchError):
        raise
    except Exception as exc:  # noqa: BLE001 -- unclassified bundle-script bug, not a transient failure
        raise NonRetryableDispatchError(
            f"bundle entrypoint {target.entrypoint!r} raised: {exc}"
        ) from exc

    if isinstance(result, TransportResult):
        return AdapterResult(
            target_type=result.transport, detail=result.detail, http_status=result.http_status
        )
    if not isinstance(result, AdapterResult):
        raise NonRetryableDispatchError(
            f"bundle entrypoint {target.entrypoint!r} returned "
            f"{type(result).__name__}, expected AdapterResult or waddle_transports.TransportResult"
        )
    return result
