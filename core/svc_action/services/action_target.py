"""ACTION-TARGET model -- the bundle-declared dispatch destination for one item.

An App Bundle's `action` stage declares, in its resolved config (either
`app_activations.config` (community-scoped) or `app_tenant_availability.
config_defaults` (tenant-wide fallback) -- see services/config_lookup.py --
or an inline `payload.target` override on the queue envelope itself), one
`action_target` block:

    action_target:
      type: webhook | rest_api | message_queue | overlay | email
      ... type-specific fields ...

:func:`parse_action_target` validates that block into a typed, immutable
:class:`ActionTarget` before any adapter ever touches it -- an invalid or
incomplete target config is rejected here (a `ActionTargetError`, caught by
the runner and dispatch-logged as a non-retryable config failure), never
partially dispatched by an adapter discovering a missing field mid-request.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

#: The five standardized adapter types this stage-runner supports.
KNOWN_TARGET_TYPES = frozenset({"webhook", "rest_api", "message_queue", "overlay", "email"})

#: HTTP methods `rest_api` may declare -- deliberately excludes methods with
#: no defined request body semantics relevant to a bundle action dispatch.
_ALLOWED_REST_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})


class ActionTargetError(ValueError):
    """Raised when an `action_target` block fails validation -- non-retryable."""


@dataclass(slots=True, frozen=True)
class ActionTarget:
    """One validated, type-specific dispatch destination.

    Every field beyond `type` is `Optional`-shaped via defaults because
    each adapter type only populates its own subset; `parse_action_target`
    is what enforces "my type's required fields are actually present" --
    this dataclass itself accepts any combination so one shape serves all
    five types without five separate dataclasses fanning out through the
    runner/dispatch registry.
    """

    type: str

    # webhook / rest_api / overlay -- outbound HTTP.
    url: str = ""
    method: str = "POST"
    headers: Mapping[str, str] = field(default_factory=dict)
    body_template: str | None = None
    secret_ref: str = ""  # HMAC signing secret (webhook only) -- from env, never logged.

    # message_queue.
    channel: str = ""

    # overlay -- community/surface path segments (falls back to the
    # envelope's own `community` when `community` is left unset here).
    community: str | None = None
    surface: str = ""

    # email.
    to_addrs: tuple[str, ...] = ()
    subject_template: str = ""


def _require(raw: Mapping[str, Any], key: str, target_type: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise ActionTargetError(
            f"action_target.type={target_type!r} requires a non-empty string {key!r}"
        )
    return value


def parse_action_target(raw: Mapping[str, Any]) -> ActionTarget:
    """Validate a raw `action_target` dict and build a typed :class:`ActionTarget`.

    Raises :class:`ActionTargetError` (a `ValueError`) on any of: missing/
    unknown `type`, missing required field for that type, or a `rest_api`
    `method` outside :data:`_ALLOWED_REST_METHODS`. Never raises on
    optional/extra fields -- an over-specified block is fine, an
    under-specified one is not.
    """
    target_type = raw.get("type")
    if target_type not in KNOWN_TARGET_TYPES:
        raise ActionTargetError(
            f"action_target.type {target_type!r} is not one of {sorted(KNOWN_TARGET_TYPES)}"
        )

    if target_type == "webhook":
        url = _require(raw, "url", target_type)
        secret_ref = _require(raw, "secret_ref", target_type)
        return ActionTarget(
            type=target_type,
            url=url,
            headers=dict(raw.get("headers", {})),
            body_template=raw.get("body_template"),
            secret_ref=secret_ref,
        )

    if target_type == "rest_api":
        url = _require(raw, "url", target_type)
        method = str(raw.get("method", "POST")).upper()
        if method not in _ALLOWED_REST_METHODS:
            raise ActionTargetError(
                f"action_target.type=rest_api method {method!r} is not one of "
                f"{sorted(_ALLOWED_REST_METHODS)}"
            )
        return ActionTarget(
            type=target_type,
            url=url,
            method=method,
            headers=dict(raw.get("headers", {})),
            body_template=raw.get("body_template"),
        )

    if target_type == "message_queue":
        channel = _require(raw, "channel", target_type)
        return ActionTarget(type=target_type, channel=channel)

    if target_type == "overlay":
        surface = _require(raw, "surface", target_type)
        community = raw.get("community")
        if community is not None and not isinstance(community, str):
            raise ActionTargetError("action_target.type=overlay community must be a string")
        return ActionTarget(type=target_type, community=community, surface=surface)

    # email
    to_raw = raw.get("to")
    if not isinstance(to_raw, list) or not to_raw or not all(isinstance(a, str) for a in to_raw):
        raise ActionTargetError(
            "action_target.type=email requires a non-empty list of string addresses in 'to'"
        )
    subject_template = _require(raw, "subject_template", target_type)
    return ActionTarget(
        type=target_type,
        to_addrs=tuple(to_raw),
        subject_template=subject_template,
        body_template=raw.get("body_template"),
    )
