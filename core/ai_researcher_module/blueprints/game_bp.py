"""
Game Lookup Blueprint
======================

REST API endpoints for the Game Lookup sub-module.
Uses a setup() function to receive injected dependencies from app.py.

Endpoints:
  POST /api/v1/game/search         — Full AI-augmented game search
  POST /api/v1/game/quick          — Quick SearXNG-only search
  GET  /api/v1/game/games/<cid>    — List community's configured games
  POST /api/v1/game/games/<cid>    — Add/configure a game (admin)
  DELETE /api/v1/game/games/<cid>/<gid> — Deactivate a game (admin)
  POST /api/v1/game/games/<cid>/copy-templates — Copy template games (admin)
  GET  /api/v1/game/items/<cid>    — Browse cached items
  GET  /api/v1/game/status         — SearXNG health + feature status
"""

import logging

from quart import Blueprint, request

logger = logging.getLogger(__name__)

game_bp = Blueprint('game', __name__, url_prefix='/api/v1/game')

# Module-level dependency references (set by setup())
_dal = None
_redis_client = None
_ai_provider = None
_safety_layer = None
_rate_limiter = None
_searxng_service = None
_get_mem0_fn = None
_config = None
_game_service = None

# Lazy imports to avoid circular dependency at module load time
_async_endpoint = None
_success_response = None
_error_response = None


def setup(
    dal, redis_client, ai_provider, safety_layer,
    rate_limiter, searxng_service, get_mem0_fn, config,
):
    """
    Inject dependencies. Called from app.py during startup.
    """
    global _dal, _redis_client, _ai_provider, _safety_layer
    global _rate_limiter, _searxng_service, _get_mem0_fn, _config
    global _game_service
    global _async_endpoint, _success_response, _error_response

    _dal = dal
    _redis_client = redis_client
    _ai_provider = ai_provider
    _safety_layer = safety_layer
    _rate_limiter = rate_limiter
    _searxng_service = searxng_service
    _get_mem0_fn = get_mem0_fn
    _config = config

    from flask_core import async_endpoint, success_response, error_response
    _async_endpoint = async_endpoint
    _success_response = success_response
    _error_response = error_response

    from services.game_lookup_service import GameLookupService
    _game_service = GameLookupService(
        dal=dal,
        redis_client=redis_client,
        ai_provider=ai_provider,
        safety_layer=safety_layer,
        rate_limiter=rate_limiter,
        searxng_service=searxng_service,
        get_mem0_fn=get_mem0_fn,
        config=config,
    )

    logger.info("Game Lookup blueprint initialized")


def _svc():
    """Get game lookup service, raising if not initialized."""
    if _game_service is None:
        raise RuntimeError("Game Lookup service not initialized — call setup() first")
    return _game_service


# =========================================================================
# Search endpoints
# =========================================================================

@game_bp.route('/search', methods=['POST'])
async def game_search():
    """Full AI-augmented game search (``!or/game <query>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().search(community_id, user_id, platform, query)

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


@game_bp.route('/quick', methods=['POST'])
async def game_quick_search():
    """Quick SearXNG-only search (``!game search <query>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().quick_search(community_id, user_id, platform, query)

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


# =========================================================================
# Game management endpoints
# =========================================================================

@game_bp.route('/games/<int:community_id>', methods=['GET'])
async def list_games(community_id: int):
    """List a community's configured games."""
    games = await _svc().get_community_games(community_id)
    return _success_response({
        'community_id': community_id,
        'games': games,
        'count': len(games),
    })


@game_bp.route('/games/<int:community_id>', methods=['POST'])
async def add_game(community_id: int):
    """Add or update a game for a community (admin only)."""
    data = await request.get_json()
    admin_id = data.get('admin_id')
    if not admin_id:
        return _error_response("admin_id is required", 400)

    name = data.get('name', '')
    if not name:
        return _error_response("name is required", 400)

    game = await _svc().add_game(community_id, str(admin_id), data)
    return _success_response(game, 201)


@game_bp.route('/games/<int:community_id>/<int:game_id>', methods=['DELETE'])
async def remove_game(community_id: int, game_id: int):
    """Deactivate a game (admin only)."""
    ok = await _svc().remove_game(community_id, game_id)
    if not ok:
        return _error_response("Failed to remove game", 400)
    return _success_response({"message": "Game deactivated"})


@game_bp.route('/games/<int:community_id>/copy-templates', methods=['POST'])
async def copy_templates(community_id: int):
    """Copy pre-seeded template games to a community."""
    data = await request.get_json()
    game_names = data.get('game_names', [])
    if not game_names:
        return _error_response("game_names list is required", 400)

    count = await _svc().copy_template_games(community_id, game_names)
    return _success_response({
        'copied': count,
        'requested': len(game_names),
    })


# =========================================================================
# Cache / status endpoints
# =========================================================================

@game_bp.route('/items/<int:community_id>', methods=['GET'])
async def get_items(community_id: int):
    """Browse cached game items with optional filters."""
    game_id = request.args.get('game_id', None, type=int)
    item_type = request.args.get('type', None)

    items = await _svc().get_cached_items(community_id, game_id, item_type)
    return _success_response({
        'community_id': community_id,
        'items': items,
        'count': len(items),
    })


@game_bp.route('/status', methods=['GET'])
async def game_status():
    """SearXNG health and feature status."""
    searxng_ok = await _searxng_service.health_check() if _searxng_service else False
    return _success_response({
        'game_lookup_enabled': True,
        'searxng_healthy': searxng_ok,
    })
