"""Additive `/api/v2` router -- `{module}/{surface}/{app_bundle}/{target}` shape.

Per the migration plan §8 D2, v2 is never a reshape of v1; it is the new
bundle-oriented surface App Bundles attach to
(docs/plans/2026-08-31-app-bundle-sdk-design.md).

`register_v2` auto-discovers every group under `blueprints.v2`
(`routers/_discovery.py`) -- this file is never edited to add a port
group. `blueprints/v2/platform.py` is the one example wired in this
scaffold, proving the pattern the other 54 controllers copy -- see its
docstring for the full tenant -> scope -> validated-DTO chain.
"""

from __future__ import annotations

from quart import Quart

import blueprints.v2 as v2_package
from routers._discovery import discover_blueprints


def register_v2(app: Quart) -> None:
    """Auto-discover and mount every v2 group's `BLUEPRINTS`."""
    for blueprint in discover_blueprints(v2_package):
        app.register_blueprint(blueprint)
