"""
Price/Deal Tracker Blueprint
==============================

REST API endpoints for the Price/Deal Tracker sub-module.
Uses a setup() function to receive injected dependencies from app.py.

Endpoints:
  POST /api/v1/price/search  — Price search (!or/price <game>)
  POST /api/v1/price/deals   — Deals search (!game deals)
  GET  /api/v1/price/status  — Feature status
"""

import logging

from quart import Blueprint, request

logger = logging.getLogger(__name__)

price_bp = Blueprint('price', __name__, url_prefix='/api/v1/price')

# Module-level dependency references (set by setup())
_dal = None
_redis_client = None
_ai_provider = None
_safety_layer = None
_rate_limiter = None
_searxng_service = None
_get_mem0_fn = None
_config = None
_price_service = None

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
    global _price_service
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

    from services.price_tracker_service import PriceTrackerService
    _price_service = PriceTrackerService(
        dal=dal,
        redis_client=redis_client,
        ai_provider=ai_provider,
        safety_layer=safety_layer,
        rate_limiter=rate_limiter,
        searxng_service=searxng_service,
        get_mem0_fn=get_mem0_fn,
        config=config,
    )

    logger.info("Price/Deal Tracker blueprint initialized")


def _svc():
    """Get price tracker service, raising if not initialized."""
    if _price_service is None:
        raise RuntimeError("Price Tracker service not initialized — call setup() first")
    return _price_service


# =========================================================================
# Search endpoints
# =========================================================================

@price_bp.route('/search', methods=['POST'])
async def price_search():
    """Price search (``!or/price <game>``)."""
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


@price_bp.route('/deals', methods=['POST'])
async def deals_search():
    """Deals search (``!game deals``)."""
    data = await request.get_json()
    community_id = data.get('community_id')
    user_id = str(data.get('user_id', ''))
    platform = data.get('platform', 'unknown')
    query = data.get('query', '')

    if not community_id or not query:
        return _error_response("community_id and query are required", 400)

    result = await _svc().deals_search(community_id, user_id, platform, query)

    if not result.success:
        status = 429 if result.blocked_reason == 'rate_limit' else 400
        return _error_response(result.content, status)

    return _success_response(result.to_dict())


# =========================================================================
# Status endpoint
# =========================================================================

@price_bp.route('/status', methods=['GET'])
async def price_status():
    """SearXNG health and feature status."""
    searxng_ok = await _searxng_service.health_check() if _searxng_service else False
    return _success_response({
        'price_tracker_enabled': True,
        'searxng_healthy': searxng_ok,
    })
