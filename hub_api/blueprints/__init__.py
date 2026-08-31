"""hub-api blueprint mounting registry.

`register_blueprints(app)` is the single call that wires every versioned
API group onto the Quart app. The 54 remaining controllers
(docs/plans/2026-08-31-hubapi-node-to-quart-migration.md's per-phase
sequence, M1..M9) land by adding a sub-blueprint to `routers/v1.py` or
`routers/v2.py` and registering it there -- not by editing this file's
logic. Health, MCP, and the two OpenAPI documents are infra-level
blueprints wired directly in `app.py` alongside this call, not through
here, since they aren't versioned business API groups.
"""

from __future__ import annotations

from quart import Quart

from routers.v1 import register_v1
from routers.v2 import register_v2


def register_blueprints(app: Quart) -> None:
    """Mount every API version group (v1 frozen, v2 additive) onto `app`."""
    register_v1(app)
    register_v2(app)
