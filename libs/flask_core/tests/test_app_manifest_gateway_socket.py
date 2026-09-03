"""Tests for the `gateway_socket` `communication_model` (svc-gateway design, 2026-09-02).

Own file, not folded into `test_app_framework.py`'s existing
`communication_model` coverage (webhook_push/rest_pull) -- this is an
additive enum member plus the enum-validation this field never had before,
so a mutation-tested regression here should not get lost among C1's
unrelated assertions.
"""

from __future__ import annotations

from flask_core.app_manifest import (
    REASON_INVALID_COMMUNICATION_MODEL,
    ManifestError,
    parse_manifest,
)

import pytest

_BASE: dict[str, object] = {
    "app_id": "waddles.bot.discord.gateway",
    "name": "Discord Gateway Ingest",
    "version": "1.0.0",
    "feature": "waddles.bot.discord",
    "module": "bot",
    "provider": "builtin",
    "is_default": True,
}


def test_gateway_socket_is_accepted_on_ingest_stage() -> None:
    data = dict(_BASE)
    data["stages"] = {
        "ingest": {
            "entrypoint": "bundles.discord_ingest:normalize",
            "consumes": ["discord.message"],
            "communication_model": "gateway_socket",
        }
    }
    manifest = parse_manifest(data)
    assert manifest.stage_specs["ingest"].communication_model == "gateway_socket"
    assert manifest.stage_specs["ingest"].consumes == ("discord.message",)


def test_webhook_push_and_rest_pull_still_accepted() -> None:
    for model in ("webhook_push", "rest_pull"):
        data = dict(_BASE)
        data["stages"] = {"action": {"communication_model": model}}
        manifest = parse_manifest(data)
        assert manifest.stage_specs["action"].communication_model == model


def test_unknown_communication_model_is_rejected() -> None:
    data = dict(_BASE)
    data["stages"] = {"ingest": {"communication_model": "carrier_pigeon"}}
    with pytest.raises(ManifestError) as exc_info:
        parse_manifest(data)
    assert exc_info.value.reason == REASON_INVALID_COMMUNICATION_MODEL


def test_missing_communication_model_still_parses() -> None:
    """A stage with no communication_model at all (the pre-existing default) is unaffected."""
    data = dict(_BASE)
    data["stages"] = {"ingest": {"entrypoint": "bundles.echo_ingest:normalize"}}
    manifest = parse_manifest(data)
    assert manifest.stage_specs["ingest"].communication_model is None
