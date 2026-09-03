"""Tests for `bundles.discord_gateway_manifest` -- the seeded Discord gateway ingest bundle."""

from __future__ import annotations

from flask_core.app_registry import AppRegistry

from bundles.discord_gateway_manifest import DISCORD_GATEWAY_MANIFEST, register_default_bundles


class TestRegisterDefaultBundles:
    def test_registers_a_valid_manifest(self) -> None:
        registry = AppRegistry()
        manifest = register_default_bundles(registry)

        assert manifest.app_id == "waddles.bot.discord.gateway"
        assert manifest.feature == "waddles.bot.discord"
        assert manifest.is_default is True

    def test_ingest_stage_declares_gateway_socket_and_discord_message(self) -> None:
        registry = AppRegistry()
        manifest = register_default_bundles(registry)

        ingest_spec = manifest.stage_specs["ingest"]
        assert ingest_spec.communication_model == "gateway_socket"
        assert ingest_spec.consumes == ("discord.message",)
        assert ingest_spec.entrypoint == "bundles.discord_ingest:normalize"

    def test_registered_manifest_is_retrievable_from_the_registry(self) -> None:
        registry = AppRegistry()
        register_default_bundles(registry)

        assert registry.get("waddles.bot.discord.gateway").app_id == "waddles.bot.discord.gateway"

    def test_raw_manifest_dict_matches_migration_082s_seeded_shape(self) -> None:
        """Loose coupling check against migration 082's DB row.

        Both must describe the identical bundle (same app_id/entrypoint/
        consumes/communication_model) -- this test only asserts the
        in-process side; the SQL itself isn't executable here.
        """
        stages = DISCORD_GATEWAY_MANIFEST["stages"]
        assert DISCORD_GATEWAY_MANIFEST["app_id"] == "waddles.bot.discord.gateway"
        assert stages["ingest"]["entrypoint"] == "bundles.discord_ingest:normalize"
        assert stages["ingest"]["consumes"] == ["discord.message"]
        assert stages["ingest"]["communication_model"] == "gateway_socket"
