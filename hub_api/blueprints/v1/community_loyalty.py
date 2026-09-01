"""v1 `community.loyalty` group -- port of Node's `loyaltyController.js` (M6 Community).

Every handler here is a thin proxy to `loyalty-interaction` (service-to-
service `X-API-Key` auth -- see `services/community_loyalty.py`), gated
by this port's own tenant + scope chain first. `@validate_response` is
skipped for the same reason as polls/forms
(`services/community_engagement_proxy.py`'s docstring): the response
shape is owned by the downstream service, not a local ORM model.

Matches the discovery contract every v1 port group follows: a module-
level `BLUEPRINTS: list[Blueprint]`, found and mounted by `routers/v1.py`'s
auto-discovery -- no edit to `routers/v1.py` needed.
"""

from __future__ import annotations

from typing import Any

from flask_core.authz import require_scope
from flask_core.tenancy import get_tenant_context, tenant_middleware
from quart import Blueprint, current_app, request

from services import community_loyalty as loyalty_client
from services.community_common import community_in_tenant
from services.community_loyalty import DEFAULT_LOYALTY_CONFIG, LoyaltyProxyError

loyalty_bp = Blueprint("v1_community_loyalty", __name__, url_prefix="/api/v1/admin")


def _tenant_ok(community_id: int) -> bool:
    ctx = get_tenant_context(request)
    assert ctx is not None  # nosec B101
    return community_in_tenant(current_app.config["dal"], community_id, ctx)


async def _write(path: str, method: str = "PUT") -> tuple[dict[str, Any], int]:
    body = await request.get_json(force=True, silent=True) or {}
    try:
        return await loyalty_client.call(method, path, json_body=body), 200
    except LoyaltyProxyError as exc:
        return {"success": False, "error": str(exc)}, 502


def _qs(**params: Any) -> str:
    pairs = [f"{k}={v}" for k, v in params.items() if v is not None]
    return f"?{'&'.join(pairs)}" if pairs else ""


# ===== Currency configuration =====


@loyalty_bp.route("/<int:community_id>/loyalty/config", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def get_config(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/config`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/config", {"config": DEFAULT_LOYALTY_CONFIG}
    )
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/config", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def update_config(community_id: int) -> tuple[dict[str, Any], int]:
    """`PUT /api/v1/admin/<id>/loyalty/config`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(f"/api/v1/admin/{community_id}/loyalty/config")


# ===== Currency management =====


@loyalty_bp.route("/<int:community_id>/loyalty/leaderboard", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def get_leaderboard(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/leaderboard`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    limit = request.args.get("limit", "25")
    offset = request.args.get("offset", "0")
    path = f"/api/v1/admin/{community_id}/loyalty/leaderboard{_qs(limit=limit, offset=offset)}"
    data = await loyalty_client.get_or_default(
        path, {"users": [], "pagination": {"total": 0, "page": 1, "limit": 25}}
    )
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/user/<int:user_id>/balance", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:admin")  # type: ignore[untyped-decorator]
async def adjust_balance(community_id: int, user_id: int) -> tuple[dict[str, Any], int]:
    """`PUT /api/v1/admin/<id>/loyalty/user/<userId>/balance`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(f"/api/v1/admin/{community_id}/loyalty/user/{user_id}/balance")


@loyalty_bp.route("/<int:community_id>/loyalty/wipe", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:admin")  # type: ignore[untyped-decorator]
async def wipe_currency(community_id: int) -> tuple[dict[str, Any], int]:
    """`POST /api/v1/admin/<id>/loyalty/wipe`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(f"/api/v1/admin/{community_id}/loyalty/wipe", method="POST")


@loyalty_bp.route("/<int:community_id>/loyalty/stats", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def get_stats(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/stats`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/stats",
        {"stats": {"total_users": 0, "total_currency": 0, "average_balance": 0}},
    )
    return data, 200


# ===== Giveaways =====


@loyalty_bp.route("/<int:community_id>/loyalty/giveaways", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def get_giveaways(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/giveaways`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    path = f"/api/v1/admin/{community_id}/loyalty/giveaways{_qs(**request.args)}"
    data = await loyalty_client.get_or_default(path, {"giveaways": []})
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/giveaways", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def create_giveaway(community_id: int) -> tuple[dict[str, Any], int]:
    """`POST /api/v1/admin/<id>/loyalty/giveaways`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    body = await request.get_json(force=True, silent=True) or {}
    try:
        data = await loyalty_client.call(
            "POST", f"/api/v1/admin/{community_id}/loyalty/giveaways", json_body=body
        )
        return data, 201
    except LoyaltyProxyError as exc:
        return {"success": False, "error": str(exc)}, 502


@loyalty_bp.route(
    "/<int:community_id>/loyalty/giveaways/<int:giveaway_id>/entries", methods=["GET"]
)
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def giveaway_entries(community_id: int, giveaway_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/giveaways/<giveawayId>/entries`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/giveaways/{giveaway_id}/entries", {"entries": []}
    )
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/giveaways/<int:giveaway_id>/draw", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def draw_giveaway(community_id: int, giveaway_id: int) -> tuple[dict[str, Any], int]:
    """`POST /api/v1/admin/<id>/loyalty/giveaways/<giveawayId>/draw`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(
        f"/api/v1/admin/{community_id}/loyalty/giveaways/{giveaway_id}/draw", method="POST"
    )


@loyalty_bp.route("/<int:community_id>/loyalty/giveaways/<int:giveaway_id>/end", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def end_giveaway(community_id: int, giveaway_id: int) -> tuple[dict[str, Any], int]:
    """`PUT /api/v1/admin/<id>/loyalty/giveaways/<giveawayId>/end`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(f"/api/v1/admin/{community_id}/loyalty/giveaways/{giveaway_id}/end")


# ===== Games =====


@loyalty_bp.route("/<int:community_id>/loyalty/games/config", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def games_config_get(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/games/config`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/games/config",
        {
            "config": {
                "slots_enabled": False,
                "coinflip_enabled": False,
                "roulette_enabled": False,
                "min_bet": 10,
                "max_bet": 10000,
            }
        },
    )
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/games/config", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def games_config_update(community_id: int) -> tuple[dict[str, Any], int]:
    """`PUT /api/v1/admin/<id>/loyalty/games/config`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(f"/api/v1/admin/{community_id}/loyalty/games/config")


@loyalty_bp.route("/<int:community_id>/loyalty/games/stats", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def games_stats(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/games/stats`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/games/stats",
        {"stats": {"total_games": 0, "total_wagered": 0, "total_payouts": 0}},
    )
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/games/recent", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def games_recent(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/games/recent`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    path = f"/api/v1/admin/{community_id}/loyalty/games/recent{_qs(**request.args)}"
    data = await loyalty_client.get_or_default(path, {"games": []})
    return data, 200


# ===== Gear shop =====


@loyalty_bp.route("/<int:community_id>/loyalty/gear/categories", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def gear_categories(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/gear/categories`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/gear/categories", {"categories": []}
    )
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/gear/items", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def gear_items_list(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/gear/items`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    path = f"/api/v1/admin/{community_id}/loyalty/gear/items{_qs(**request.args)}"
    data = await loyalty_client.get_or_default(path, {"items": []})
    return data, 200


@loyalty_bp.route("/<int:community_id>/loyalty/gear/items", methods=["POST"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def gear_items_create(community_id: int) -> tuple[dict[str, Any], int]:
    """`POST /api/v1/admin/<id>/loyalty/gear/items`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    body = await request.get_json(force=True, silent=True) or {}
    try:
        data = await loyalty_client.call(
            "POST", f"/api/v1/admin/{community_id}/loyalty/gear/items", json_body=body
        )
        return data, 201
    except LoyaltyProxyError as exc:
        return {"success": False, "error": str(exc)}, 502


@loyalty_bp.route("/<int:community_id>/loyalty/gear/items/<int:item_id>", methods=["PUT"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def gear_items_update(community_id: int, item_id: int) -> tuple[dict[str, Any], int]:
    """`PUT /api/v1/admin/<id>/loyalty/gear/items/<itemId>`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    return await _write(f"/api/v1/admin/{community_id}/loyalty/gear/items/{item_id}")


@loyalty_bp.route("/<int:community_id>/loyalty/gear/items/<int:item_id>", methods=["DELETE"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:write")  # type: ignore[untyped-decorator]
async def gear_items_delete(community_id: int, item_id: int) -> tuple[dict[str, Any], int]:
    """`DELETE /api/v1/admin/<id>/loyalty/gear/items/<itemId>`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    try:
        data = await loyalty_client.call(
            "DELETE", f"/api/v1/admin/{community_id}/loyalty/gear/items/{item_id}"
        )
        return data, 200
    except LoyaltyProxyError as exc:
        return {"success": False, "error": str(exc)}, 502


@loyalty_bp.route("/<int:community_id>/loyalty/gear/stats", methods=["GET"])
@tenant_middleware  # type: ignore[untyped-decorator]
@require_scope("community.loyalty:read")  # type: ignore[untyped-decorator]
async def gear_stats(community_id: int) -> tuple[dict[str, Any], int]:
    """`GET /api/v1/admin/<id>/loyalty/gear/stats`."""
    if not _tenant_ok(community_id):
        return {"success": False, "error": "Community not found"}, 404
    data = await loyalty_client.get_or_default(
        f"/api/v1/admin/{community_id}/loyalty/gear/stats",
        {"stats": {"total_items": 0, "total_sold": 0, "total_revenue": 0}},
    )
    return data, 200


BLUEPRINTS: list[Blueprint] = [loyalty_bp]
