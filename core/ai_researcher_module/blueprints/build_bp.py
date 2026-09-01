"""
Build/Loadout Advisor Blueprint
=================================

REST API endpoints for the Build/Loadout Advisor sub-module.
Uses a setup() function to receive injected dependencies from app.py.

Endpoints:
  POST /api/v1/build/search   — Build search (!or/build <game> <class>)
  POST /api/v1/build/meta     — Meta lookup (!or/meta <game>)
  GET  /api/v1/build/status   — Feature status
"""

import logging

from quart import Blueprint, request

logger = logging.getLogger(__name__)

build_bp = Blueprint('build', __name__, url_prefix='/api/v1/build')

# Module-level dependency references (set by setup())
_dal = None
_redis_client = None
_ai_provider = None
_safety_layer = None
_rate_limiter = None
_searxng_service = None
_get_mem0_fn = None
_config = None
_build_service = None

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
    global _build_service
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

    from services.build_advisor_service import BuildAdvisorService
    _build_service = BuildAdvisorService(
        dal=dal,
        redis_client=redis_client,
        ai_provider=ai_provider,
        safety_layer=safety_layer,
        rate_limiter=rate_limiter,
        searxng_service=searxng_service,
        get_mem0_fn=get_mem0_fn,
        config=config,
    )

    logger.info("Build/Loadout Advisor blueprint initialized")


def _svc():
    """Get build advisor service, raising if not initialized."""
    if _build_service is None:
        raise RuntimeError(
            "Build Advisor service not initialized — call setup() first"
        )
    return _build_service


# =========================================================================
# Search endpoints
# =========================================================================

@build_bp.route('/search', methods=['POST'])
async def build_search():
    """Build search (``!or/build <game> <class>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')
    class_name = data.get('class_name', '')
    game_name = data.get('game_name', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().search(
        community_id, user_id, platform, query,
        class_name=class_name, game_name=game_name,
    )

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


@build_bp.route('/meta', methods=['POST'])
async def build_meta():
    """Meta lookup (``!or/meta <game>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')
    game_name = data.get('game_name', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().meta_search(
        community_id, user_id, platform, query,
        game_name=game_name,
    )

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


# =========================================================================
# Status endpoint
# =========================================================================

@build_bp.route('/status', methods=['GET'])
async def build_status():
    """SearXNG health and feature status."""
    searxng_ok = await _searxng_service.health_check() if _searxng_service else False
    return _success_response({
        'build_advisor_enabled': True,
        'searxng_healthy': searxng_ok,
    })
