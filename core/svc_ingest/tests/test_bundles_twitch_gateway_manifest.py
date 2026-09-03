"""Tests for `bundles.twitch_gateway_manifest` -- the seeded Twitch chat + EventSub bundles."""

from __future__ import annotations

from flask_core.app_registry import AppRegistry

from bundles.twitch_gateway_manifest import (
    TWITCH_EVENTSUB_MANIFEST,
    TWITCH_GATEWAY_MANIFEST,
    register_default_bundles,
)


class TestRegisterDefaultBundles:
    def test_registers_both_valid_manifests(self) -> None:
        registry = AppRegistry()
        gateway, eventsub = register_default_bundles(registry)

        assert gateway.app_id == "waddles.bot.twitch.gateway"
        assert gateway.feature == "waddles.bot.twitch"
        assert gateway.is_default is True

        assert eventsub.app_id == "waddles.bot.twitchevents.eventsub"
        assert eventsub.feature == "waddles.bot.twitchevents"
        assert eventsub.is_default is True

    def test_gateway_ingest_stage_declares_twitch_message(self) -> None:
        registry = AppRegistry()
        gateway, _ = register_default_bundles(registry)

        ingest_spec = gateway.stage_specs["ingest"]
        assert ingest_spec.communication_model == "gateway_socket"
        assert ingest_spec.consumes == ("twitch.message",)
        assert ingest_spec.entrypoint == "bundles.twitch_ingest:normalize"

    def test_eventsub_ingest_stage_declares_twitch_eventsub(self) -> None:
        registry = AppRegistry()
        _, eventsub = register_default_bundles(registry)

        ingest_spec = eventsub.stage_specs["ingest"]
        assert ingest_spec.communication_model == "webhook_push"
        assert ingest_spec.consumes == ("twitch.eventsub",)
        assert ingest_spec.entrypoint == "bundles.twitch_eventsub_ingest:normalize"

    def test_both_manifests_are_retrievable_from_the_registry(self) -> None:
        registry = AppRegistry()
        register_default_bundles(registry)

        assert registry.get("waddles.bot.twitch.gateway").app_id == "waddles.bot.twitch.gateway"
        assert (
            registry.get("waddles.bot.twitchevents.eventsub").app_id
            == "waddles.bot.twitchevents.eventsub"
        )

    def test_raw_manifest_dicts_match_migration_082s_seeded_shape(self) -> None:
        """Loose coupling check against migration 082's DB rows.

        Both must describe the identical bundles (same app_id/entrypoint/
        consumes); the SQL itself isn't executable here.
        """
        gateway_stages = TWITCH_GATEWAY_MANIFEST["stages"]
        assert TWITCH_GATEWAY_MANIFEST["app_id"] == "waddles.bot.twitch.gateway"
        assert gateway_stages["ingest"]["entrypoint"] == "bundles.twitch_ingest:normalize"
        assert gateway_stages["ingest"]["consumes"] == ["twitch.message"]

        eventsub_stages = TWITCH_EVENTSUB_MANIFEST["stages"]
        assert TWITCH_EVENTSUB_MANIFEST["app_id"] == "waddles.bot.twitchevents.eventsub"
        assert eventsub_stages["ingest"]["entrypoint"] == "bundles.twitch_eventsub_ingest:normalize"
        assert eventsub_stages["ingest"]["consumes"] == ["twitch.eventsub"]
