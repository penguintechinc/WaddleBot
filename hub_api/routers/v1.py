"""Frozen `/api/v1` router -- matches the existing Node hub_module contract.

Per docs/plans/2026-08-31-hubapi-node-to-quart-migration.md §8 D2: v1 is
ported controller-group by controller-group, 1:1 unchanged, protecting
the React hub-webui app (`admin/hub_module/frontend/src/services/api.js`
is the pinned contract source of truth -- every ported path must match
it byte-for-byte). This module is the mount point the 55 controllers
land in phase by phase (M1..M9 in the migration plan); nothing here
reshapes a v1 path. `/api/v2` (`v2.py`) is the additive, bundle-oriented
API -- never a rename of v1.

Only a single placeholder lives here today: `POST /auth/login`, a 501
stub proving where Core Identity/Auth (phase M1) attaches, and the exact
path the public OpenAPI document (`openapi/spec_builder.py`) documents.
"""

from __future__ import annotations

from quart import Blueprint, Quart

v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@v1_bp.route("/auth/login", methods=["POST"])
async def login_stub() -> tuple[dict[str, str], int]:
    """M1 placeholder -- real OAuth/JWT login lands with Core Identity/Auth (phase M1).

    Deliberately unauthenticated (login always is) and deliberately not
    wired to `flask_core.auth.create_jwt_token` yet -- porting the real
    3-platform OAuth flow is out of scope for the M0 scaffold.
    """
    return {
        "error": "not_implemented",
        "message": "auth login is not yet ported -- see M1 in the hub-api migration plan",
    }, 501


def register_v1(app: Quart) -> None:
    """Mount the frozen v1 API group. Each M1..M9 phase adds its own sub-blueprint here."""
    app.register_blueprint(v1_bp)
