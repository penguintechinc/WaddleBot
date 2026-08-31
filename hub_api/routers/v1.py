"""Frozen `/api/v1` router -- matches the existing Node hub_module contract.

Per docs/plans/2026-08-31-hubapi-node-to-quart-migration.md §8 D2: v1 is
ported controller-group by controller-group, 1:1 unchanged, protecting
the React hub-webui app (`admin/hub_module/frontend/src/services/api.js`
is the pinned contract source of truth -- every ported path must match
it byte-for-byte). `/api/v2` (`v2.py`) is the additive, bundle-oriented
API -- never a rename of v1.

`register_v1` auto-discovers every group under `blueprints.v1`
(`routers/_discovery.py`) -- this file is never edited to add a port
group. The 55 controllers land phase by phase (M1..M9 in the migration
plan) by dropping a module in `blueprints/v1/`, nothing here.
"""

from __future__ import annotations

from quart import Quart

import blueprints.v1 as v1_package
from routers._discovery import discover_blueprints


def register_v1(app: Quart) -> None:
    """Auto-discover and mount every v1 group's `BLUEPRINTS`."""
    for blueprint in discover_blueprints(v1_package):
        app.register_blueprint(blueprint)
