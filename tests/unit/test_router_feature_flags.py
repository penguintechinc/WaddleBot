"""Unit tests for the Router's feature-flag / module-enable dispatch gate.

The router's ``CommandProcessor`` normally pulls in aiohttp, quart, pydal and
the local ``config`` / ``services`` packages, none of which are installed in the
unit-test environment. Following the stdlib-only approach in
``test_feature_flags.py``, this module:

* stubs the heavy top-level imports in ``sys.modules`` so ``command_processor``
  can be loaded by file path, and
* loads the real ``FeatureFlagService`` (also by file path),

then exercises the real ``_dispatch_gate``, ``execute_command`` and
``_process_interaction`` coroutines bound to a lightweight fake ``self`` (the
class ``__init__`` — which builds a ContextService/grpc manager — is never run).

Coverage:
  * flag-disabled blocks dispatch (module HTTP call never made)
  * flag absent allows dispatch (fail-open)
  * core module (identity/workflow) bypasses BOTH the module toggle and the flag
  * the interaction path is now gated (previously unchecked)
"""
import asyncio
import fnmatch
import importlib.util
import os
import sys
import types

import pytest

_HERE = os.path.dirname(__file__)
_ROUTER = os.path.join(_HERE, "..", "..", "processing", "router_module")
_FF_PATH = os.path.join(
    _HERE, "..", "..", "libs", "flask_core", "flask_core", "feature_flags.py"
)


def run(coro):
    """Drive a coroutine to completion without pytest-asyncio."""
    return asyncio.run(coro)


# --- Load the real FeatureFlagService standalone ----------------------------
def _load_feature_flags():
    spec = importlib.util.spec_from_file_location("_ff_router_test", _FF_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


feature_flags = _load_feature_flags()
FeatureFlagService = feature_flags.FeatureFlagService


# --- Load command_processor with the heavy deps stubbed out -----------------
def _install_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


def _load_command_processor():
    if "_router_command_processor" in sys.modules:
        return sys.modules["_router_command_processor"]

    # Minimal Config with only the attributes touched at import / call time.
    class _Config:
        GRPC_ENABLED = False
        STREAM_PIPELINE_ENABLED = False
        SERVICE_API_KEY = ""
        ROUTER_REQUEST_TIMEOUT = 5
        ROUTER_ENTITY_CACHE_TTL = 300

    # aiohttp is only referenced inside methods we stub on the fake self, but the
    # module imports it at top level, so a bare stand-in is enough.
    _install_stub("aiohttp")
    _install_stub("config", Config=_Config)

    services_pkg = types.ModuleType("services")
    services_pkg.__path__ = []  # mark as a package
    sys.modules["services"] = services_pkg

    class _CommandInfo:  # only used for typing / isinstance-free access
        pass

    _install_stub(
        "services.command_registry",
        CommandRegistry=object,
        CommandInfo=_CommandInfo,
    )
    _install_stub("services.context_service", ContextService=object)
    _install_stub("services.grpc_clients", get_grpc_manager=lambda: None)
    _install_stub("services.ai_chatter_config_cache", AiChatterConfigCache=object)

    path = os.path.join(_ROUTER, "services", "command_processor.py")
    spec = importlib.util.spec_from_file_location("_router_command_processor", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


cp = _load_command_processor()
CommandProcessor = cp.CommandProcessor
CORE_MODULE_NAMES = cp.CORE_MODULE_NAMES


# --- Fakes ------------------------------------------------------------------
class StubDAL:
    """Emulates PyDAL executesql for the feature_flags table.

    ``rows`` is a list of (community_id, platform, is_enabled, rollout_pct).
    """

    def __init__(self, rows=None):
        self.rows = rows or []

    def executesql(self, sql, params=None):
        # Feature-flag query: params == [flag_key, community_id]
        if params and len(params) == 2 and "feature_flags" in sql:
            community_id = params[1]
            return [r for r in self.rows if r[0] is None or r[0] == community_id]
        # Interaction module-URL lookup / anything else -> no rows.
        return []


def make_flag_service(rows=None):
    return FeatureFlagService(redis_client=None, dal=StubDAL(rows=rows))


class FakeSelf:
    """A stand-in ``self`` carrying only what the gated coroutines touch."""

    def __init__(self, *, flag_rows=None, community_id=5, module_enabled=True):
        self.feature_flag_service = make_flag_service(rows=flag_rows)
        self.dal = StubDAL()
        self._community_id = community_id
        self._module_enabled = module_enabled
        self.module_calls = []  # (url, payload) for each dispatch attempt
        self.handled_responses = []

    async def _get_community_for_entity(self, entity_id, user_id=None, platform=None):
        return self._community_id

    async def _is_module_enabled(self, module_name, community_id):
        return self._module_enabled

    async def _call_module_with_retry(self, url, payload, max_retries=3):
        self.module_calls.append((url, payload))
        return {"ok": True}

    async def handle_module_response(self, data):
        self.handled_responses.append(data)

    # Bind the real gate/dispatch coroutines.
    _dispatch_gate = CommandProcessor._dispatch_gate
    execute_command = CommandProcessor.execute_command
    _process_interaction = CommandProcessor._process_interaction


class Cmd:
    """Lightweight CommandInfo stand-in."""

    def __init__(self, module_name, module_url="http://mod:8000",
                 is_enabled=True, cooldown_seconds=0):
        self.module_name = module_name
        self.module_url = module_url
        self.is_enabled = is_enabled
        self.cooldown_seconds = cooldown_seconds


def with_command(fake, cmd):
    """Attach a command_registry that returns ``cmd``."""
    class _Registry:
        async def get_command(self, command, community_id):
            return cmd
    fake.command_registry = _Registry()
    return fake


# --- _dispatch_gate directly ------------------------------------------------
def test_gate_blocks_when_flag_disabled():
    fake = FakeSelf(flag_rows=[(None, None, False, 100)])  # global kill-switch
    gate = run(fake._dispatch_gate("loyalty", 5))
    assert gate is not None
    assert gate["success"] is False
    assert "disabled" in gate["error"]


def test_gate_allows_when_flag_absent_fail_open():
    fake = FakeSelf(flag_rows=[])  # no flag rows -> fail open
    assert run(fake._dispatch_gate("loyalty", 5)) is None


def test_gate_blocks_when_module_toggle_off():
    fake = FakeSelf(flag_rows=[], module_enabled=False)
    gate = run(fake._dispatch_gate("loyalty", 5))
    assert gate is not None
    assert "module is disabled" in gate["error"]


def test_gate_core_module_bypasses_both_gates():
    # Module toggle OFF *and* a global flag kill-switch -> core still passes.
    for core in CORE_MODULE_NAMES:
        fake = FakeSelf(
            flag_rows=[(None, None, False, 100)], module_enabled=False
        )
        assert run(fake._dispatch_gate(core, 5)) is None
    assert CORE_MODULE_NAMES == frozenset({"identity", "workflow"})


def test_gate_flag_is_platform_scoped():
    # Disabled only for twitch; discord stays enabled.
    fake = FakeSelf(flag_rows=[(None, "twitch", False, 100)])
    assert run(fake._dispatch_gate("loyalty", 5, "twitch")) is not None
    assert run(fake._dispatch_gate("loyalty", 5, "discord")) is None


# --- execute_command path ---------------------------------------------------
def test_execute_command_flag_disabled_blocks_dispatch():
    fake = with_command(
        FakeSelf(flag_rows=[(None, None, False, 100)]),
        Cmd("loyalty"),
    )
    result = run(fake.execute_command("!points", "e1", "u1", "!points", "s1"))
    assert result["success"] is False
    assert "disabled" in result["error"]
    assert result["session_id"] == "s1"
    assert fake.module_calls == []  # module was never dispatched to


def test_execute_command_flag_absent_allows_dispatch():
    fake = with_command(FakeSelf(flag_rows=[]), Cmd("loyalty"))
    result = run(fake.execute_command("!points", "e1", "u1", "!points", "s1"))
    assert result["success"] is True
    assert len(fake.module_calls) == 1  # module was dispatched to


def test_execute_command_core_module_bypasses_disabled_flag():
    fake = with_command(
        FakeSelf(flag_rows=[(None, None, False, 100)], module_enabled=False),
        Cmd("identity"),
    )
    result = run(fake.execute_command("!whoami", "e1", "u1", "!whoami", "s1"))
    assert result["success"] is True
    assert len(fake.module_calls) == 1  # core module dispatched despite kill-switch


# --- interaction path (previously ungated) ----------------------------------
def _interaction(fake, custom_id, platform="twitch"):
    event_data = {"message_type": "button_click", "platform": platform}
    metadata = {"custom_id": custom_id, "values": {}}
    return run(
        fake._process_interaction(event_data, "e1", "u1", "s1", metadata)
    )


def test_interaction_flag_disabled_blocks_dispatch():
    fake = FakeSelf(flag_rows=[(None, None, False, 100)])
    result = _interaction(fake, "loyalty:buy:item_1")
    assert result["success"] is False
    assert "disabled" in result["error"]
    assert result["session_id"] == "s1"
    assert fake.module_calls == []  # never POSTed to the module


def test_interaction_flag_absent_allows_dispatch():
    fake = FakeSelf(flag_rows=[])
    result = _interaction(fake, "loyalty:buy:item_1")
    assert result["success"] is True
    assert len(fake.module_calls) == 1


def test_interaction_core_module_bypasses_gates():
    fake = FakeSelf(flag_rows=[(None, None, False, 100)], module_enabled=False)
    result = _interaction(fake, "workflow:run:wf_9")
    assert result["success"] is True
    assert len(fake.module_calls) == 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
