"""Additive `/api/v2` router -- `{module}/{surface}/{app_bundle}/{target}` shape.

Per the migration plan §8 D2, v2 is never a reshape of v1; it is the new
bundle-oriented surface App Bundles attach to
(docs/plans/2026-08-31-app-bundle-sdk-design.md). Each SCCEMBS module
gets its own sub-blueprint mounted here as it's ported;
`blueprints/platform.py` is the one example wired in this scaffold,
proving the pattern the other 54 controllers copy -- see its docstring
for the full tenant -> scope -> validated-DTO chain.
"""

from __future__ import annotations

from quart import Blueprint, Quart

from blueprints.platform import platform_bp

v2_bp = Blueprint("api_v2", __name__, url_prefix="/api/v2")
# Nested blueprint registration composes url_prefixes: "/api/v2" + "/core/platform/default"
# + "/status" => "/api/v2/core/platform/default/status".
v2_bp.register_blueprint(platform_bp)


def register_v2(app: Quart) -> None:
    """Mount the additive v2 API group."""
    app.register_blueprint(v2_bp)
