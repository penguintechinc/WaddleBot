"""
MCP surface -- tool derivation and the below-the-surface gate chain
======================================================================

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Interaction surfaces:
gRPC, REST, MCP``: hub-api is reached three ways, and MCP tools "derive
from Feature contracts" rather than being hand-written, so a tool can
never widen the scopes its own Feature already declares, and versioning
is solved because the Feature's own ``id@version`` is already the
compatibility unit ("`bot.shoutout@1` is already the compatibility
unit").

This module is the transport-agnostic half of the MCP surface:

- :func:`mcp_tool_from_contract` / :func:`list_tools_for_tenant` -- tool
  derivation and per-tenant listing. Listing is an authorization
  decision, not a static manifest (design doc: "the set of MCP tools an
  agent can see is per tenant") -- a thin wrapper over
  :func:`flask_core.feature_registry.entitled_features`, so a Free tenant
  never sees an Enterprise tool in the first place.
- :func:`authorize_and_resolve_tool_call` -- the gate chain
  ``tools/call`` must run through: scope, then feature/licensing, then
  App resolution. Tenant itself is verified one level up, by whichever
  transport wraps this (see :mod:`flask_core.mcp_routes`), using the
  exact same JWT tenant-claim verification REST uses -- "One
  authorization path, or MCP becomes the bypass" is the reason this gate
  lives here, below the transport, rather than being reimplemented per
  surface.

Deliberately NOT here: an App execution runtime. No such runtime exists
yet anywhere in this codebase -- :mod:`flask_core.app_binding` only
resolves *which* App is bound to a Feature slot, per the design doc's
Apps section. ``tools/call`` therefore dispatches only as far as
resolving the bound App and reporting its identity back; wiring an App's
actual handler is follow-on work once that runtime exists, same "thin
dispatch" boundary the task spec draws.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Optional, Sequence, Tuple

from .app_binding import BindingError, InstallationLookup, resolve_app
from .app_manifest import AppManifest
from .app_registry import AppRegistry
from .auth import SCOPE_BUNDLES
from .feature_contract import FeatureContract
from .feature_registry import FeatureCheck, FeatureRegistry, FeatureRegistryError
from .feature_registry import entitled_features as _entitled_features
from .feature_registry import get_registry as get_feature_registry

#: MCP protocol version this transport implements -- see mcp_routes.py's
#: module docstring for the Streamable HTTP transport choice.
MCP_PROTOCOL_VERSION = "2025-06-18"


class McpAuthorizationError(Exception):
    """
    Raised by :func:`authorize_and_resolve_tool_call` for any gate
    failure -- unknown tool, missing scope, feature not entitled, or no
    App bound. ``reason`` is a stable machine-checkable code, mirroring
    :class:`~flask_core.feature_contract.FeatureContractError`'s shape, so
    callers and tests assert on *why* a call was denied, not just that it
    was.
    """

    def __init__(self, reason: str, detail: str) -> None:
        self.reason = reason
        super().__init__(f"{reason}: {detail}")


REASON_UNKNOWN_TOOL = "unknown_tool"
REASON_SCOPE_DENIED = "scope_denied"
REASON_FEATURE_DISABLED = "feature_disabled"
REASON_NO_APP_BOUND = "no_app_bound"


@dataclass(slots=True, frozen=True)
class McpTool:
    """One MCP tool definition, derived from exactly one Feature contract -- never hand-written."""

    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """MCP wire shape: ``{"name", "description", "inputSchema"}``."""
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


_SEGMENT = r"[a-z0-9][a-z0-9_-]*"
# <module>.<feature>@<version> -- matches feature_contract.py's id shape plus the
# version suffix that makes each tool name a single, unambiguous compatibility unit.
_TOOL_NAME_RE = re.compile(
    rf"^(?P<feature_id>{_SEGMENT}\.{_SEGMENT})@(?P<version>[1-9]\d*)$"
)


def tool_name_for_contract(contract: FeatureContract) -> str:
    """
    The tool name for a Feature contract: ``<id>@<version>``.

    Baking the version into the name means a Feature version bump ships
    as a new, distinct tool rather than silently reinterpreting calls
    aimed at an old one.
    """
    return f"{contract.id}@{contract.version}"


def mcp_tool_from_contract(contract: FeatureContract) -> McpTool:
    """
    Build the MCP tool definition for ``contract``.

    The input schema is deliberately generic (an optional
    ``community_id`` plus a passthrough ``arguments`` object): no
    per-Feature argument schema exists yet in the spine, and App-specific
    parameter validation is follow-on work once a real execution runtime
    exists (see module docstring).
    """
    return McpTool(
        name=tool_name_for_contract(contract),
        description=(
            f"Invoke the {contract.id!r} feature "
            f"(module={contract.module}, min_tier={contract.min_tier})."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "community_id": {
                    "type": ["integer", "null"],
                    "description": "Community to scope this call to, or omit/null for tenant-wide.",
                },
                "arguments": {
                    "type": "object",
                    "description": "Feature-specific arguments, passed through to the resolved App.",
                    "additionalProperties": True,
                },
            },
            "required": [],
        },
    )


async def list_tools_for_tenant(
    *,
    tenant: str,
    community: Optional[int] = None,
    contracts: Optional[Tuple[FeatureContract, ...]] = None,
    check: Optional[FeatureCheck] = None,
) -> List[McpTool]:
    """
    The full ``tools/list`` result for ``tenant`` -- an authorization
    decision, not a static manifest. A Feature whose flag/license gate
    does not pass for this tenant (and, if given, ``community``) never
    becomes a tool; see :func:`flask_core.feature_registry.entitled_features`
    for the two-gate evaluation this wraps.
    """
    entitled = await _entitled_features(
        tenant=tenant, community=community, contracts=contracts, check=check
    )
    return [mcp_tool_from_contract(contract) for contract in entitled]


_ROLE_RE = re.compile(r"^(global|tenant|community):(admin|maintainer|viewer)$")


def effective_scopes(roles: Sequence[str]) -> FrozenSet[str]:
    """
    Union the scopes granted by every ``{level}:{bundle}`` role in
    ``roles`` -- security.md's per-level scope-bundle table, held in
    ``auth.SCOPE_BUNDLES``, reused here rather than re-declared so MCP and
    REST can never drift onto two different scope vocabularies. A role
    string outside the ``{level}:{bundle}`` shape grants nothing -- fail
    closed, not an exception, since a caller's ``roles`` claim may
    legitimately carry product-specific names this ladder doesn't cover.
    """
    scopes: set[str] = set()
    for role in roles:
        match = _ROLE_RE.match(role)
        if match is None:
            continue
        level, bundle = match.group(1), match.group(2)
        scopes.update(SCOPE_BUNDLES.get(level, {}).get(bundle, ()))
    return frozenset(scopes)


def _scope_grants(required: str, granted: FrozenSet[str]) -> bool:
    """True if some granted scope (possibly wildcarded, e.g. ``*:write``) covers ``required``."""
    return any(fnmatch.fnmatchcase(required, pattern) for pattern in granted)


def has_required_scopes(required: FrozenSet[str], granted: FrozenSet[str]) -> bool:
    """True only if EVERY scope in ``required`` is covered by ``granted``."""
    return all(_scope_grants(scope, granted) for scope in required)


def _lookup_contract(
    tool_name: str, *, registry: Optional[FeatureRegistry]
) -> FeatureContract:
    """Resolve ``tool_name`` back to its Feature contract, or raise ``REASON_UNKNOWN_TOOL``."""
    match = _TOOL_NAME_RE.match(tool_name)
    if match is None:
        raise McpAuthorizationError(
            REASON_UNKNOWN_TOOL, f"{tool_name!r} is not a well-formed tool name"
        )

    reg = registry if registry is not None else get_feature_registry()
    try:
        contract = reg.get(match.group("feature_id"))
    except FeatureRegistryError:
        raise McpAuthorizationError(
            REASON_UNKNOWN_TOOL, f"no Feature registered for tool {tool_name!r}"
        ) from None

    if contract.version != int(match.group("version")):
        raise McpAuthorizationError(
            REASON_UNKNOWN_TOOL,
            f"tool {tool_name!r} does not match the registered version ({contract.version})",
        )
    return contract


async def authorize_and_resolve_tool_call(
    tool_name: str,
    *,
    tenant: str,
    community: Optional[int],
    granted_scopes: FrozenSet[str],
    installations: InstallationLookup,
    registry: Optional[FeatureRegistry] = None,
    app_registry: Optional[AppRegistry] = None,
    check: Optional[FeatureCheck] = None,
) -> Tuple[FeatureContract, AppManifest]:
    """
    The gate chain ``tools/call`` must run through -- shared with, never
    bypassing, REST's ordering: tenant -> scope -> feature/licensing
    (design doc "One authorization path, or MCP becomes the bypass").
    ``tenant`` is assumed already verified by the transport (the same JWT
    tenant-claim check REST uses) before this is ever called; this
    function is the scope and feature/licensing half of the chain, plus
    App resolution.

    Raises :class:`McpAuthorizationError` at the first failing gate, in
    order: unknown tool, missing scope, feature not entitled for
    ``tenant``/``community``, no App bound. Never partially executes past
    a failed gate -- a caller cannot learn "the feature is on" by having
    the scope check pass first and vice versa beyond what the exception's
    single ``reason`` reveals.
    """
    contract = _lookup_contract(tool_name, registry=registry)

    if not has_required_scopes(contract.requires_scopes, granted_scopes):
        raise McpAuthorizationError(
            REASON_SCOPE_DENIED,
            f"tool {tool_name!r} requires scopes {sorted(contract.requires_scopes)}",
        )

    check_fn = check
    if check_fn is None:
        # Local import: avoids pulling feature_flags.py's posthog/penguin_licensing
        # dependency chain into every caller that injects a fake check (tests).
        from .feature_flags import feature_enabled

        check_fn = feature_enabled

    enabled = await check_fn(
        contract.flag, tenant=tenant, community=community, default=False
    )
    if not enabled:
        raise McpAuthorizationError(
            REASON_FEATURE_DISABLED,
            f"feature {contract.id!r} is not entitled for tenant {tenant!r}",
        )

    try:
        app = await resolve_app(
            # app_binding's `feature` key is the AppManifest-namespaced form
            # (`waddles.<module>.<feature>`, per app_manifest.py's `_FEATURE_RE`)
            # -- which is exactly `contract.flag` (parse_feature_contract already
            # enforces `flag == f"waddles.{id}"`), never the unprefixed `contract.id`.
            contract.flag,
            tenant=tenant,
            community=community,
            installations=installations,
            registry=app_registry,
        )
    except BindingError as exc:
        raise McpAuthorizationError(REASON_NO_APP_BOUND, str(exc)) from exc

    return contract, app
