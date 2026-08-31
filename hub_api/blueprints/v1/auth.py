"""v1 `auth` group -- today, just the M1 placeholder login stub.

Matches the discovery contract every v1 port group follows: a module-
level `BLUEPRINTS: list[Blueprint]`, found and mounted by `routers/v1.py`'s
auto-discovery -- no edit to `routers/v1.py` needed. Real OAuth/JWT login
(Core Identity/Auth, migration plan phase M1) replaces this stub in
place, in this same file.
"""

from __future__ import annotations

from quart import Blueprint

auth_bp = Blueprint("v1_auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.route("/login", methods=["POST"])
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


BLUEPRINTS: list[Blueprint] = [auth_bp]
