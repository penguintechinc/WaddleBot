"""Canonical DB + tenant/community accessor for stateful App Bundles.

A bundle's entrypoint signatures are frozen (`docs/APP_BUNDLE_AUTHORING.md`
Sec2): `async def transform(event: PlatformEvent) -> PlatformEvent | None`
for process, `async def <name>(envelope: StageEnvelope, config, *,
http_client) -> TransportResult` for action. Neither carries a DAL, and
`transform`'s signature doesn't even carry the envelope -- so a stateful
bundle (fetch a stored quote, mark a user welcomed, tally poll votes) has
no parameter to reach a DB connection or its own tenant/community scope
through. This module is the one sanctioned side channel, replacing the
divergent module-level `set_dal()`-per-bundle pattern some bundles
improvised (e.g. `social_welcome_process.py`) with a single shared
mechanism every bundle and every stage runner uses identically.

Two independent pieces of state, because they change on different
schedules:

- The DAL (:func:`set_bundle_dal` / :func:`get_bundle_dal`) is bound
  **once**, by a stage runner's own startup (`app.py`'s `before_serving`),
  and never changes for the life of the process -- a plain module global
  is correct and sufficient, the same way a DB connection pool is
  process-wide in every other service in this repo.
- The tenant/community/app_id scope (:func:`bundle_context` /
  :func:`get_bundle_context`) changes on **every envelope** -- a stage
  runner drains one bundle's queue at a time today
  (`core/svc_process/runner.py`/`core/svc_action/runner.py`, a plain
  `while True: rpop` loop, never concurrent `asyncio.gather` fan-out), but
  a `contextvars.ContextVar` is used instead of a second module global so
  this stays correct if that ever changes -- each concurrent asyncio task
  gets its own isolated view instead of racing on shared mutable state.

A bundle NEVER calls `set_bundle_dal`/`bundle_context` itself -- those are
the stage runner's job, invoked around each entrypoint call. A bundle only
ever reads, via `get_bundle_dal()`/`get_bundle_context()`.
"""

from __future__ import annotations

import contextvars
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type-only -- avoids a runtime `import pydal` (via .database) so this
    # stays a lightweight leaf module, same rationale as stream_pipeline.py/
    # stage_runner.py (module docstrings) not depending on the heavy
    # pydal/quart/authlib stack `flask_core/__init__.py` eagerly imports.
    from .database import AsyncDAL


class BundleRuntimeError(RuntimeError):
    """Raised by `get_bundle_dal()`/`get_bundle_context()` when the runner never bound one.

    Always indicates a wiring bug, never a data condition: either a stage
    runner that has no DB (svc-ingest, which has no DAL at all) is being
    asked to serve a stateful bundle, or a test constructed a bundle call
    without first calling `set_bundle_dal()`/entering `bundle_context()`.
    """


_dal: AsyncDAL | None = None


def set_bundle_dal(dal: AsyncDAL) -> None:
    """Bind the process-wide DAL every `get_bundle_dal()` call will return.

    Called exactly once, by a stage runner's own startup (e.g.
    `core/svc_process/app.py`'s `before_serving` hook, mirroring
    `core/svc_action/app.py`'s existing `AsyncDAL` construction) --
    never by a bundle itself.

    Args:
        dal: The `flask_core.AsyncDAL` this process's bundles will share.
    """
    global _dal
    _dal = dal


def get_bundle_dal() -> AsyncDAL:
    """Return the DAL bound by `set_bundle_dal()`.

    A bundle calls this from inside its own `transform()`/action-entrypoint
    body -- the frozen entrypoint signatures carry no DAL parameter.

    Returns:
        The `AsyncDAL` instance the current stage runner bound at startup.

    Raises:
        BundleRuntimeError: No runner has ever called `set_bundle_dal()` in
            this process -- e.g. svc-ingest (no DB), or a test that forgot
            to wire one.
    """
    if _dal is None:
        raise BundleRuntimeError(
            "no DAL bound -- this stage runner must call "
            "flask_core.bundle_runtime.set_bundle_dal() during startup "
            "before any bundle entrypoint can call get_bundle_dal() "
            "(see docs/APP_BUNDLE_AUTHORING.md, 'Accessing the database / "
            "shared state')"
        )
    return _dal


def reset_bundle_dal_for_tests() -> None:
    """Clear the bound DAL. Test-only -- prevents state leaking across test modules.

    Not used by production code; a stage runner's own process lifetime
    naturally scopes `set_bundle_dal()` to "once at startup", but a pytest
    session runs many independent test modules in one process, so a
    fixture teardown should call this to keep tests isolated from each
    other's bound DAL.
    """
    global _dal
    _dal = None


@dataclass(slots=True, frozen=True)
class BundleContext:
    """The tenant/community/app_id scope of the envelope currently being processed.

    Bound by a stage runner immediately before invoking a bundle's
    entrypoint (once per envelope, via `bundle_context()`); a bundle reads
    it with `get_bundle_context()` to scope its own DB queries -- never
    from `event.payload[...]`, which is untrusted, unscoped platform data
    (security.md Tenant Isolation: the isolation boundary comes from the
    envelope the runner popped off this bundle's own per-tenant Valkey
    key, never from data a remote user can influence).
    """

    tenant: str
    community: str | None
    app_id: str


_context: contextvars.ContextVar[BundleContext | None] = contextvars.ContextVar(
    "waddlebot_bundle_context", default=None
)


def get_bundle_context() -> BundleContext:
    """Return the `BundleContext` bound for the envelope currently being processed.

    A bundle calls this from inside its own `transform()`/action-entrypoint
    body to scope a DB query by tenant/community -- `transform(event)`
    itself never receives the envelope, so this is the only way a process
    bundle reaches its tenant/community scope.

    Returns:
        The `BundleContext` the enclosing `bundle_context()` block bound.

    Raises:
        BundleRuntimeError: Called outside any `bundle_context()` block --
            e.g. a stage runner that forgot to wrap its entrypoint call, or
            a test invoking a bundle function directly without entering
            `bundle_context()` first.
    """
    ctx = _context.get()
    if ctx is None:
        raise BundleRuntimeError(
            "no bundle context bound -- this stage runner must wrap each "
            "bundle entrypoint call in "
            "flask_core.bundle_runtime.bundle_context(tenant=..., "
            "community=..., app_id=...) before a bundle can call "
            "get_bundle_context() (see docs/APP_BUNDLE_AUTHORING.md, "
            "'Accessing the database / shared state')"
        )
    return ctx


@contextmanager
def bundle_context(
    *, tenant: str, community: str | None, app_id: str
) -> Iterator[BundleContext]:
    """Scope tenant/community/app_id for one bundle entrypoint invocation.

    A stage runner wraps each `transform()`/action-entrypoint call, e.g.
    `core/svc_process/runner.py::_transform_and_enqueue`::

        with bundle_context(
            tenant=envelope_in.tenant,
            community=envelope_in.community,
            app_id=envelope_in.app_id,
        ):
            event_out = await transform_fn(event_in)

    Uses a `contextvars.ContextVar` (not a plain module global) so this is
    safe under concurrent asyncio tasks -- see the module docstring's
    rationale. The bound context is always cleared on exit, including on
    an exception raised by the wrapped call.

    Args:
        tenant: `StageEnvelope.tenant` -- the tenant slug this envelope
            belongs to.
        community: `StageEnvelope.community` -- `None` for a tenant-wide
            activation.
        app_id: `StageEnvelope.app_id` -- this bundle's own `app_catalog`
            identifier.

    Yields:
        The `BundleContext` now bound for the duration of the block.
    """
    ctx = BundleContext(tenant=tenant, community=community, app_id=app_id)
    token = _context.set(ctx)
    try:
        yield ctx
    finally:
        _context.reset(token)
