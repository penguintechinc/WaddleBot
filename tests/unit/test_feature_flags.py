"""Unit tests for flask_core.feature_flags.FeatureFlagService.

The service under test only depends on the standard library, so it is loaded
directly by file path to avoid importing the full ``flask_core`` package
(which pulls in pydal / redis / quart). Async coroutines are driven with
``asyncio.run`` so the suite needs no pytest-asyncio plugin or config.
"""
import asyncio
import fnmatch
import importlib.util
import json
import os
import sys

import pytest

# --- Load feature_flags.py standalone (stdlib-only module) ------------------
_MODULE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "libs", "flask_core", "flask_core", "feature_flags.py",
)
_spec = importlib.util.spec_from_file_location("_ff_under_test", _MODULE_PATH)
assert _spec and _spec.loader
feature_flags = importlib.util.module_from_spec(_spec)
# Register before exec so @dataclass(slots=True) can resolve the module.
sys.modules[_spec.name] = feature_flags
_spec.loader.exec_module(feature_flags)

FeatureFlagService = feature_flags.FeatureFlagService
create_feature_flag_service = feature_flags.create_feature_flag_service
RELOAD_CHANNEL = feature_flags.RELOAD_CHANNEL


def run(coro):
    """Drive a coroutine to completion without pytest-asyncio."""
    return asyncio.run(coro)


# --- Fakes ------------------------------------------------------------------
class FakeRedis:
    """Minimal in-memory async stand-in for a raw redis.asyncio client."""

    def __init__(self):
        self.store: dict[str, bytes] = {}
        self.published: list[tuple[str, str]] = []

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, ttl, value):
        if isinstance(value, str):
            value = value.encode()
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)

    async def publish(self, channel, message):
        self.published.append((channel, message))

    async def scan_iter(self, match="*"):
        for key in list(self.store.keys()):
            if fnmatch.fnmatch(key, match):
                yield key


class StubDAL:
    """Emulates PyDAL executesql for the feature_flags table.

    ``rows`` is a list of (community_id, platform, is_enabled, rollout_pct).
    Emulates the ``community_id IS NULL OR community_id = %s`` filter so the
    Python-side specificity resolution is exercised realistically.
    """

    def __init__(self, rows=None, raise_exc=None):
        self.rows = rows or []
        self.raise_exc = raise_exc
        self.calls = 0

    def executesql(self, sql, params):
        self.calls += 1
        if self.raise_exc is not None:
            raise self.raise_exc
        community_id = params[1]
        return [
            r for r in self.rows
            if r[0] is None or r[0] == community_id
        ]


def make_service(rows=None, raise_exc=None, redis=None, ttl=300):
    dal = StubDAL(rows=rows, raise_exc=raise_exc)
    svc = create_feature_flag_service(redis, dal, default_ttl=ttl)
    return svc, dal, redis


# --- Resolution specificity -------------------------------------------------
def test_community_override_beats_global_killswitch():
    """MOST SPECIFIC wins: a community row overrides a global kill-switch."""
    rows = [
        (None, None, False, 100),  # global kill-switch
        (5, None, True, 100),      # community 5 override -> on
    ]
    svc, _, _ = make_service(rows)
    assert run(svc.is_enabled("flag", community_id=5)) is True


def test_global_killswitch_applies_to_other_communities():
    """A community without its own row falls back to the global kill-switch."""
    rows = [
        (None, None, False, 100),  # global kill-switch
        (5, None, True, 100),      # only community 5 overrides
    ]
    svc, _, _ = make_service(rows)
    assert run(svc.is_enabled("flag", community_id=99)) is False


def test_community_scope_dominates_platform_specificity():
    """Community specificity dominates: a community-wide row beats a
    global platform-specific row even though the latter names the platform."""
    rows = [
        (None, "twitch", True, 100),  # global, twitch-specific -> on
        (5, None, False, 100),        # community 5, all platforms -> off
    ]
    svc, _, _ = make_service(rows)
    assert run(svc.is_enabled("flag", community_id=5, platform="twitch")) is False


def test_platform_specific_beats_platform_null_same_community():
    rows = [
        (5, None, True, 100),        # community 5, all platforms
        (5, "twitch", False, 100),   # community 5, twitch -> most specific
    ]
    svc, _, _ = make_service(rows)
    assert run(svc.is_enabled("flag", community_id=5, platform="twitch")) is False
    # Different platform falls back to the community-wide row.
    assert run(svc.is_enabled("flag", community_id=5, platform="discord")) is True


def test_global_platform_specific_selected_for_global_scope():
    rows = [
        (None, None, True, 100),
        (None, "twitch", False, 100),
    ]
    svc, _, _ = make_service(rows)
    assert run(svc.is_enabled("flag", community_id=None, platform="twitch")) is False
    assert run(svc.is_enabled("flag", community_id=None, platform="discord")) is True


def test_matched_row_disabled_returns_false():
    svc, _, _ = make_service([(None, None, False, 100)])
    assert run(svc.is_enabled("flag")) is False


# --- Absent flag / defaults -------------------------------------------------
def test_absent_flag_returns_default_true():
    svc, _, _ = make_service([])
    assert run(svc.is_enabled("missing")) is True


def test_absent_flag_respects_explicit_default_false():
    svc, _, _ = make_service([])
    assert run(svc.is_enabled("missing", default=False)) is False


# --- Rollout bucketing ------------------------------------------------------
def test_rollout_100_always_true():
    svc, _, _ = make_service([(None, None, True, 100)])
    assert run(svc.is_enabled("flag", community_id=1)) is True


def test_rollout_0_always_false():
    svc, _, _ = make_service([(None, None, True, 0)])
    assert run(svc.is_enabled("flag", community_id=1)) is False


def test_rollout_bucketing_is_deterministic():
    """Same (flag_key, community_id) -> same decision. No cache involved."""
    svc, _, _ = make_service([(None, None, True, 50)], redis=None)
    first = run(svc.is_enabled("flag", community_id=42))
    second = run(svc.is_enabled("flag", community_id=42))
    third = run(svc.is_enabled("flag", community_id=42))
    assert first == second == third


def test_rollout_distribution_roughly_matches_pct():
    """Over many community_ids, ~50% land enabled at rollout_pct=50."""
    svc, _, _ = make_service([(None, None, True, 50)], redis=None)
    enabled = sum(
        1 for cid in range(2000)
        if run(svc.is_enabled("dist_flag", community_id=cid))
    )
    ratio = enabled / 2000
    assert 0.42 < ratio < 0.58, f"ratio={ratio}"


# --- Error handling (fail-open) --------------------------------------------
def test_db_error_returns_default():
    svc, _, _ = make_service(raise_exc=RuntimeError("db down"))
    assert run(svc.is_enabled("flag", default=True)) is True
    assert run(svc.is_enabled("flag", default=False)) is False


def test_cache_read_error_returns_default():
    class BrokenRedis(FakeRedis):
        async def get(self, key):
            raise RuntimeError("redis down")

    svc, _, _ = make_service([(None, None, True, 100)], redis=BrokenRedis())
    assert run(svc.is_enabled("flag", default=True)) is True


# --- Caching ----------------------------------------------------------------
def test_cache_hit_skips_db():
    redis = FakeRedis()
    key = FeatureFlagService._cache_key("flag", 5, "twitch")
    redis.store[key] = b"0"
    svc, dal, _ = make_service(raise_exc=RuntimeError("should not query"), redis=redis)
    result = run(svc.is_enabled("flag", community_id=5, platform="twitch"))
    assert result is False
    assert dal.calls == 0  # DB never touched on a cache hit


def test_miss_populates_cache():
    redis = FakeRedis()
    svc, dal, _ = make_service([(None, None, True, 100)], redis=redis)
    assert run(svc.is_enabled("flag", community_id=7)) is True
    assert dal.calls == 1
    key = FeatureFlagService._cache_key("flag", 7, None)
    assert redis.store[key] == b"1"
    # Second call is served from cache.
    assert run(svc.is_enabled("flag", community_id=7)) is True
    assert dal.calls == 1


# --- Reload publish / handle -----------------------------------------------
def test_publish_reload_emits_expected_payload():
    redis = FakeRedis()
    svc, _, _ = make_service([], redis=redis)
    run(svc.publish_reload("flag", community_id=5))
    assert len(redis.published) == 1
    channel, message = redis.published[0]
    assert channel == RELOAD_CHANNEL
    assert json.loads(message) == {"flag_key": "flag", "community_id": 5}


def test_handle_reload_invalidates_all_flag_keys():
    redis = FakeRedis()
    redis.store[FeatureFlagService._cache_key("flag", 1, "twitch")] = b"1"
    redis.store[FeatureFlagService._cache_key("flag", 2, None)] = b"0"
    redis.store[FeatureFlagService._cache_key("flag", None, "discord")] = b"1"
    redis.store[FeatureFlagService._cache_key("other", 1, None)] = b"1"  # untouched
    svc, _, _ = make_service([], redis=redis)

    run(svc.handle_reload({"flag_key": "flag", "community_id": None}))

    remaining = list(redis.store.keys())
    assert remaining == [FeatureFlagService._cache_key("other", 1, None)]


def test_handle_reload_accepts_pubsub_envelope():
    redis = FakeRedis()
    redis.store[FeatureFlagService._cache_key("flag", 1, None)] = b"1"
    svc, _, _ = make_service([], redis=redis)

    envelope = {
        "type": "message",
        "channel": RELOAD_CHANNEL,
        "data": json.dumps({"flag_key": "flag", "community_id": None}),
    }
    run(svc.handle_reload(envelope))
    assert FeatureFlagService._cache_key("flag", 1, None) not in redis.store


def test_handle_reload_ignores_missing_flag_key():
    redis = FakeRedis()
    redis.store[FeatureFlagService._cache_key("flag", 1, None)] = b"1"
    svc, _, _ = make_service([], redis=redis)
    run(svc.handle_reload({"community_id": 5}))  # no flag_key -> no-op
    assert FeatureFlagService._cache_key("flag", 1, None) in redis.store


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
