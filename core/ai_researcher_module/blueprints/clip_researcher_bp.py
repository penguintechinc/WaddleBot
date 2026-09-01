"""
Clip/Highlight Researcher Blueprint
=====================================

REST API endpoints for the Clip/Highlight Researcher sub-module.
Uses a setup() function to receive injected dependencies from app.py.

Endpoints:
  POST /api/v1/clip-research/clips      — Clip search (!or/clips <game> <topic>)
  POST /api/v1/clip-research/highlight   — Highlight/player search (!or/highlight <player>)
  GET  /api/v1/clip-research/status      — Feature status
"""

import logging

from quart import Blueprint, request

logger = logging.getLogger(__name__)

clip_researcher_bp = Blueprint('clip_researcher', __name__, url_prefix='/api/v1/clip-research')

# Module-level dependency references (set by setup())
_dal = None
_redis_client = None
_ai_provider = None
_safety_layer = None
_rate_limiter = None
_searxng_service = None
_get_mem0_fn = None
_config = None
_clip_service = None

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
    global _clip_service
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

    from services.clip_researcher_service import ClipResearcherService
    _clip_service = ClipResearcherService(
        dal=dal,
        redis_client=redis_client,
        ai_provider=ai_provider,
        safety_layer=safety_layer,
        rate_limiter=rate_limiter,
        searxng_service=searxng_service,
        get_mem0_fn=get_mem0_fn,
        config=config,
    )

    logger.info("Clip/Highlight Researcher blueprint initialized")


def _svc():
    """Get clip researcher service, raising if not initialized."""
    if _clip_service is None:
        raise RuntimeError("Clip Researcher service not initialized — call setup() first")
    return _clip_service


# =========================================================================
# Search endpoints
# =========================================================================

@clip_researcher_bp.route('/clips', methods=['POST'])
async def clip_search():
    """Clip search (``!or/clips <game> <topic>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')
    game_name = data.get('game_name')
    topic = data.get('topic')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().search_clips(
        community_id, user_id, platform, query,
        game_name=game_name, topic=topic,
    )

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


@clip_researcher_bp.route('/highlight', methods=['POST'])
async def highlight_search():
    """Highlight/player search (``!or/highlight <player>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')
    player_name = data.get('player_name')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().search_highlights(
        community_id, user_id, platform, query,
        player_name=player_name,
    )

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


# =========================================================================
# Status endpoint
# =========================================================================

@clip_researcher_bp.route('/status', methods=['GET'])
async def clip_researcher_status():
    """SearXNG health and feature status."""
    searxng_ok = await _searxng_service.health_check() if _searxng_service else False
    return _success_response({
        'clip_researcher_enabled': True,
        'searxng_healthy': searxng_ok,
    })
