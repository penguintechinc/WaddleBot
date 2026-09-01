"""Per-(community x app) Valkey isolation key builders (App Bundle SDK Phase C4).

Covers `bundle_stream_key`/`bundle_config_key`/`bundle_state_key`/
`bundle_consumer_group` and the `BundleIsolationKeys` struct added to
`stream_pipeline.py` per design doc `2026-08-31-app-bundle-sdk-design.md`
Sec6.2/Sec7.2. Kept in its own file (not the shared `conftest.py`) since these
are pure-function tests with no fixture dependencies.
"""

from __future__ import annotations

import pytest

from flask_core.stream_pipeline import (
    BundleIsolationKeys,
    bundle_config_key,
    bundle_consumer_group,
    bundle_state_key,
    bundle_stream_key,
)

TENANT = "tenant-1"
COMMUNITY = "community-1"
APP_ID = "waddles.bot.giveaway.giveaway-classic"


def test_bundle_stream_key_community_activation() -> None:
    """A community-scoped activation renders `c:{community}` verbatim."""
    assert bundle_stream_key(TENANT, COMMUNITY, APP_ID, "ingest") == (
        f"waddles:t:{TENANT}:c:{COMMUNITY}:app:{APP_ID}:ingest"
    )


def test_bundle_stream_key_tenant_wide_uses_literal_c_tenant() -> None:
    """`community=None` (tenant-wide activation) renders `c:_tenant`, not an
    omitted segment — every key stays uniformly parseable regardless of
    activation scope, per design doc Sec7.2.
    """
    key = bundle_stream_key(TENANT, None, APP_ID, "process")
    assert key == f"waddles:t:{TENANT}:c:_tenant:app:{APP_ID}:process"
    assert ":c:_tenant:" in key


@pytest.mark.parametrize("stage", ["ingest", "process", "action"])
def test_bundle_stream_key_all_stages(stage: str) -> None:
    """All three pipeline stages produce independent, correctly-suffixed keys."""
    key = bundle_stream_key(TENANT, COMMUNITY, APP_ID, stage)
    assert key.endswith(f":{stage}")
    assert key == f"waddles:t:{TENANT}:c:{COMMUNITY}:app:{APP_ID}:{stage}"


def test_bundle_config_key() -> None:
    assert bundle_config_key(TENANT, COMMUNITY, APP_ID) == (
        f"waddles:t:{TENANT}:c:{COMMUNITY}:app:{APP_ID}:cfg"
    )


def test_bundle_config_key_tenant_wide() -> None:
    assert bundle_config_key(TENANT, None, APP_ID) == (
        f"waddles:t:{TENANT}:c:_tenant:app:{APP_ID}:cfg"
    )


def test_bundle_state_key() -> None:
    assert bundle_state_key(TENANT, COMMUNITY, APP_ID) == (
        f"waddles:t:{TENANT}:c:{COMMUNITY}:app:{APP_ID}:state"
    )


def test_bundle_state_key_tenant_wide() -> None:
    assert bundle_state_key(TENANT, None, APP_ID) == (
        f"waddles:t:{TENANT}:c:_tenant:app:{APP_ID}:state"
    )


def test_bundle_consumer_group() -> None:
    """Consumer group naming feeds the existing `create_consumer_group`
    mechanism unchanged — only the naming convention is new.
    """
    assert bundle_consumer_group(APP_ID, "action") == f"{APP_ID}:action-group"


def test_bundle_stream_key_preserves_dots_in_app_id() -> None:
    """`app_id` is dot-delimited (e.g. `waddles.bot.shoutout.default`); dots
    are valid Valkey key bytes so the id passes through intact, unescaped.
    """
    dotted = "waddles.bot.shoutout.default"
    key = bundle_stream_key(TENANT, COMMUNITY, dotted, "ingest")
    assert f":app:{dotted}:ingest" in key
    assert key.count(dotted) == 1


@pytest.mark.parametrize(
    ("community_a", "app_id_a", "stage_a", "community_b", "app_id_b", "stage_b"),
    [
        # differ only by community
        (COMMUNITY, APP_ID, "ingest", "community-2", APP_ID, "ingest"),
        # differ only by app_id
        (COMMUNITY, APP_ID, "ingest", COMMUNITY, "waddles.bot.other.default", "ingest"),
        # differ only by stage
        (COMMUNITY, APP_ID, "ingest", COMMUNITY, APP_ID, "process"),
        # community vs tenant-wide
        (COMMUNITY, APP_ID, "ingest", None, APP_ID, "ingest"),
    ],
)
def test_distinct_triples_yield_distinct_stream_keys(
    community_a: str | None,
    app_id_a: str,
    stage_a: str,
    community_b: str | None,
    app_id_b: str,
    stage_b: str,
) -> None:
    key_a = bundle_stream_key(TENANT, community_a, app_id_a, stage_a)
    key_b = bundle_stream_key(TENANT, community_b, app_id_b, stage_b)
    assert key_a != key_b


def test_distinct_app_ids_yield_distinct_consumer_groups() -> None:
    assert bundle_consumer_group(APP_ID, "ingest") != bundle_consumer_group(
        "waddles.bot.other.default", "ingest"
    )


@pytest.mark.parametrize(
    "bad_stage", ["response", "inbound", "actions", "", "INGEST", "ingest "]
)
def test_bundle_stream_key_rejects_invalid_stage(bad_stage: str) -> None:
    with pytest.raises(ValueError):
        bundle_stream_key(TENANT, COMMUNITY, APP_ID, bad_stage)


@pytest.mark.parametrize("bad_stage", ["response", "", "PROCESS"])
def test_bundle_consumer_group_rejects_invalid_stage(bad_stage: str) -> None:
    with pytest.raises(ValueError):
        bundle_consumer_group(APP_ID, bad_stage)


def test_bundle_isolation_keys_struct_matches_free_functions() -> None:
    """`BundleIsolationKeys` is a typed struct wrapper — it must never drift
    from the free-function builders it delegates to.
    """
    keys = BundleIsolationKeys(tenant=TENANT, community=COMMUNITY, app_id=APP_ID)
    assert keys.stream_key("ingest") == bundle_stream_key(
        TENANT, COMMUNITY, APP_ID, "ingest"
    )
    assert keys.config_key == bundle_config_key(TENANT, COMMUNITY, APP_ID)
    assert keys.state_key == bundle_state_key(TENANT, COMMUNITY, APP_ID)
    assert keys.consumer_group("action") == bundle_consumer_group(APP_ID, "action")


def test_bundle_isolation_keys_is_slotted_and_frozen() -> None:
    """Slotted per repo dataclass convention; frozen since a key namespace is
    a value object, not mutable state.
    """
    keys = BundleIsolationKeys(tenant=TENANT, community=COMMUNITY, app_id=APP_ID)
    assert not hasattr(keys, "__dict__")
    with pytest.raises(Exception):
        keys.tenant = "other-tenant"  # type: ignore[misc]


def test_bundle_isolation_keys_tenant_wide() -> None:
    keys = BundleIsolationKeys(tenant=TENANT, community=None, app_id=APP_ID)
    assert keys.config_key == f"waddles:t:{TENANT}:c:_tenant:app:{APP_ID}:cfg"
