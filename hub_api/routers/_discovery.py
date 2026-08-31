"""Blueprint auto-discovery -- the v1/v2 port extension point.

`register_v1`/`register_v2` (`v1.py`, `v2.py`) are one-line callers of
`discover_blueprints` against `blueprints.v1`/`blueprints.v2`. Neither
router file is ever edited to add a port group: a port agent drops
exactly one module, `blueprints/v{1,2}/<group>.py`, exposing a module-
level `BLUEPRINTS: list[Blueprint]` (each blueprint's `url_prefix`
already the full `/api/v{1,2}/...` path -- discovery registers it as-is,
no extra prefix wrapping). This removes `routers/v1.py`/`routers/v2.py`
as a shared-file collision point for the parallel controller-port wave
(docs/plans/2026-08-31-hubapi-node-to-quart-migration.md, M1..M9).
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from types import ModuleType

from quart import Blueprint

logger = logging.getLogger(__name__)


def discover_blueprints(package: ModuleType) -> list[Blueprint]:
    """Import every submodule of `package` (sorted by name) and collect its `BLUEPRINTS`.

    A submodule without a module-level `BLUEPRINTS` list is skipped with
    an info-level log line, not an error -- e.g. a future non-route
    helper module living alongside its group's blueprint module (a
    `services.py`, a shared `models.py`, etc). Sorted iteration keeps
    registration order deterministic regardless of filesystem/import
    ordering, which otherwise varies by OS and is not guaranteed by
    `pkgutil.iter_modules` itself.
    """
    discovered: list[Blueprint] = []
    module_infos = sorted(
        pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."),
        key=lambda info: info.name,
    )
    for module_info in module_infos:
        module = importlib.import_module(module_info.name)
        blueprints = getattr(module, "BLUEPRINTS", None)
        if blueprints is None:
            logger.info("router.discovery.skipped_no_blueprints module=%s", module_info.name)
            continue
        discovered.extend(blueprints)
    return discovered
