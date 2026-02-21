"""
Tech Troubleshooter Blueprint
===============================

REST API endpoints for the Tech Troubleshooter sub-module.
Uses a setup() function to receive injected dependencies from app.py.

Endpoints:
  POST /api/v1/tech/fix           — Full AI troubleshooting (!or/fix <issue>)
  POST /api/v1/tech/troubleshoot  — Quick SearXNG-only troubleshoot (!or/troubleshoot <error>)
  GET  /api/v1/tech/status        — Feature status
"""

import logging

from quart import Blueprint, request

logger = logging.getLogger(__name__)

tech_bp = Blueprint('tech', __name__, url_prefix='/api/v1/tech')

# Module-level dependency references (set by setup())
_dal = None
_redis_client = None
_ai_provider = None
_safety_layer = None
_rate_limiter = None
_searxng_service = None
_get_mem0_fn = None
_config = None
_tech_service = None

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
    global _tech_service
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

    from services.tech_troubleshooter_service import TechTroubleshooterService
    _tech_service = TechTroubleshooterService(
        dal=dal,
        redis_client=redis_client,
        ai_provider=ai_provider,
        safety_layer=safety_layer,
        rate_limiter=rate_limiter,
        searxng_service=searxng_service,
        get_mem0_fn=get_mem0_fn,
        config=config,
    )

    logger.info("Tech Troubleshooter blueprint initialized")


def _svc():
    """Get tech troubleshooter service, raising if not initialized."""
    if _tech_service is None:
        raise RuntimeError("Tech Troubleshooter service not initialized — call setup() first")
    return _tech_service


# =========================================================================
# Search endpoints
# =========================================================================

@tech_bp.route('/fix', methods=['POST'])
async def tech_fix():
    """Full AI troubleshooting (``!or/fix <issue>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().fix(community_id, user_id, platform, query)

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


@tech_bp.route('/troubleshoot', methods=['POST'])
async def tech_troubleshoot():
    """Quick SearXNG-only troubleshoot (``!or/troubleshoot <error>``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().troubleshoot(community_id, user_id, platform, query)

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


# =========================================================================
# Status endpoint
# =========================================================================

@tech_bp.route('/status', methods=['GET'])
async def tech_status():
    """SearXNG health and feature status."""
    searxng_ok = await _searxng_service.health_check() if _searxng_service else False
    return _success_response({
        'tech_troubleshooter_enabled': True,
        'searxng_healthy': searxng_ok,
    })
