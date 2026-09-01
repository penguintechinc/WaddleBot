"""svc-presentation blueprint auto-discovery registry.

Mirrors `hub_api/blueprints/__init__.py` + `hub_api/routers/_discovery.py`'s
pattern: `register_blueprints(app)` imports every submodule of this
package and collects its module-level `BLUEPRINTS: list[Blueprint]`. A new
surface group (e.g. a future activated bundle's own `presentation`
component) lands by dropping one new module here with its own
`BLUEPRINTS` list -- `app.py` is never edited to add one.
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import TYPE_CHECKING

from quart import Blueprint

if TYPE_CHECKING:
    from quart import Quart

logger = logging.getLogger(__name__)


def _discover_blueprints() -> list[Blueprint]:
    """Import every submodule of this package (sorted by name) and collect its `BLUEPRINTS`."""
    import blueprints as package

    discovered: list[Blueprint] = []
    module_infos = sorted(
        pkgutil.iter_modules(package.__path__, prefix=f"{package.__name__}."),
        key=lambda info: info.name,
    )
    for module_info in module_infos:
        module = importlib.import_module(module_info.name)
        blueprints = getattr(module, "BLUEPRINTS", None)
        if blueprints is None:
            logger.info("blueprints.discovery.skipped_no_blueprints module=%s", module_info.name)
            continue
        discovered.extend(blueprints)
    return discovered


def register_blueprints(app: Quart) -> None:
    """Auto-discover and mount every group's `BLUEPRINTS` onto `app`."""
    for blueprint in _discover_blueprints():
        app.register_blueprint(blueprint)
