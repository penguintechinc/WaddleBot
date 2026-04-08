"""
Quote Interaction Module - Quart Application

Manages community quotes with full-text search and pagination support.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'libs'))  # noqa: E402

from quart import Quart, Blueprint, request  # noqa: E402
from flask_core import (  # noqa: E402
    setup_aaa_logging,
    init_database,
    async_endpoint,
    success_response,
    error_response,
    create_health_blueprint
)
from config import Config  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
quote_service = None


@app.before_serving
async def startup():
    """Initialize database and services on startup"""
    global dal, quote_service
    from services.quote_service import QuoteService

    logger.system("Starting quote_interaction_module", action="startup")

    # Initialize database with AsyncDAL
    dal = init_database(
        Config.DATABASE_URL,
        pool_size=Config.DB_POOL_SIZE,
        read_replica_uri=Config.READ_REPLICA_URL
    )
    app.config['dal'] = dal
    quote_service = QuoteService(dal)
    app.config['quote_service'] = quote_service

    logger.system("quote_interaction_module started", result="SUCCESS")


@api_bp.route('/status', methods=['GET'])
@async_endpoint
async def status():
    """Get module status"""
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION
    })


@api_bp.route('/quotes', methods=['POST'])
@async_endpoint
async def add_quote():
    """Add a new quote"""
    try:
        data = await request.get_json()

        # Validate required fields
        if not data.get('community_id') or not data.get('text'):
            return error_response(
                "Missing required fields: community_id, text",
                status_code=400
            )

        quote = await quote_service.add_quote(
            community_id=data['community_id'],
            text=data['text'],
            author=data.get('author'),
            added_by_user_id=data.get('added_by_user_id'),
            quoted_user_id=data.get('quoted_user_id'),
            platform=data.get('platform'),
            context=data.get('context'),
            tags=data.get('tags'),
            is_approved=data.get('is_approved', Config.AUTO_APPROVE_QUOTES)
        )

        return success_response(quote, status_code=201)

    except Exception as e:
        logger.error(f"Failed to add quote: {e}")
        return error_response(f"Failed to add quote: {str(e)}", status_code=500)


@api_bp.route('/quotes/<int:quote_id>', methods=['GET'])
@async_endpoint
async def get_quote(quote_id):
    """Get a specific quote by ID"""
    try:
        quote = await quote_service.get_quote(quote_id)

        if not quote:
            return error_response("Quote not found", status_code=404)

        return success_response(quote)

    except Exception as e:
        logger.error(f"Failed to get quote: {e}")
        return error_response(f"Failed to get quote: {str(e)}", status_code=500)


@api_bp.route('/quotes/random/<int:community_id>', methods=['GET'])
@async_endpoint
async def get_random_quote(community_id):
    """Get a random quote from community"""
    try:
        quote = await quote_service.get_random_quote(community_id)

        if not quote:
            return error_response(
                "No quotes available for this community",
                status_code=404
            )

        return success_response(quote)

    except Exception as e:
        logger.error(f"Failed to get random quote: {e}")
        return error_response(f"Failed to get random quote: {str(e)}", status_code=500)


@api_bp.route('/quotes/list/<int:community_id>', methods=['GET'])
@async_endpoint
async def list_quotes(community_id):
    """List quotes for a community with pagination"""
    try:
        limit = min(
            int(request.args.get('limit', Config.DEFAULT_PAGE_SIZE)),
            Config.MAX_PAGE_SIZE
        )
        offset = int(request.args.get('offset', 0))
        only_approved = request.args.get('approved', 'true').lower() == 'true'

        quotes, total_count = await quote_service.get_quotes(
            community_id=community_id,
            limit=limit,
            offset=offset,
            only_approved=only_approved
        )

        return success_response({
            'quotes': quotes,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_count,
                'has_more': (offset + limit) < total_count
            }
        })

    except Exception as e:
        logger.error(f"Failed to list quotes: {e}")
        return error_response(f"Failed to list quotes: {str(e)}", status_code=500)


@api_bp.route('/quotes/search/<int:community_id>', methods=['GET'])
@async_endpoint
async def search_quotes(community_id):
    """Search quotes using full-text search"""
    try:
        query = request.args.get('q', '').strip()

        if not query or len(query) < Config.MIN_SEARCH_QUERY_LENGTH:
            return error_response(
                f"Search query must be at least {Config.MIN_SEARCH_QUERY_LENGTH} characters",
                status_code=400
            )

        limit = min(
            int(request.args.get('limit', Config.DEFAULT_PAGE_SIZE)),
            Config.MAX_PAGE_SIZE
        )
        offset = int(request.args.get('offset', 0))

        quotes, total_count = await quote_service.search_quotes(
            community_id=community_id,
            query=query,
            limit=limit,
            offset=offset
        )

        return success_response({
            'query': query,
            'quotes': quotes,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_count,
                'has_more': (offset + limit) < total_count
            }
        })

    except Exception as e:
        logger.error(f"Failed to search quotes: {e}")
        return error_response(f"Failed to search quotes: {str(e)}", status_code=500)


@api_bp.route('/quotes/author/<int:community_id>', methods=['GET'])
@async_endpoint
async def get_by_author(community_id):
    """Get quotes by a specific author"""
    try:
        author = request.args.get('author', '').strip()

        if not author:
            return error_response("Author name is required", status_code=400)

        limit = min(
            int(request.args.get('limit', Config.DEFAULT_PAGE_SIZE)),
            Config.MAX_PAGE_SIZE
        )
        offset = int(request.args.get('offset', 0))

        quotes, total_count = await quote_service.get_quotes_by_author(
            community_id=community_id,
            author=author,
            limit=limit,
            offset=offset
        )

        return success_response({
            'author': author,
            'quotes': quotes,
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': total_count,
                'has_more': (offset + limit) < total_count
            }
        })

    except Exception as e:
        logger.error(f"Failed to get quotes by author: {e}")
        return error_response(f"Failed to get quotes by author: {str(e)}", status_code=500)


@api_bp.route('/quotes/<int:quote_id>', methods=['PUT'])
@async_endpoint
async def update_quote(quote_id):
    """Update a quote"""
    try:
        data = await request.get_json()

        success = await quote_service.update_quote(
            quote_id=quote_id,
            text=data.get('text'),
            author=data.get('author'),
            context=data.get('context'),
            tags=data.get('tags'),
            is_approved=data.get('is_approved'),
            platform=data.get('platform')
        )

        if not success:
            return error_response("Quote not found", status_code=404)

        return success_response({
            'id': quote_id,
            'message': 'Quote updated successfully'
        })

    except Exception as e:
        logger.error(f"Failed to update quote: {e}")
        return error_response(f"Failed to update quote: {str(e)}", status_code=500)


@api_bp.route('/quotes/<int:quote_id>', methods=['DELETE'])
@async_endpoint
async def delete_quote(quote_id):
    """Delete a quote (soft-delete)"""
    try:
        success = await quote_service.delete_quote(quote_id)

        if not success:
            return error_response("Quote not found", status_code=404)

        return success_response({
            'id': quote_id,
            'message': 'Quote deleted successfully'
        })

    except Exception as e:
        logger.error(f"Failed to delete quote: {e}")
        return error_response(f"Failed to delete quote: {str(e)}", status_code=500)


@api_bp.route('/quotes/stats/<int:community_id>', methods=['GET'])
@async_endpoint
async def get_stats(community_id):
    """Get quote statistics for a community"""
    try:
        stats = await quote_service.get_quote_stats(community_id)
        return success_response(stats)

    except Exception as e:
        logger.error(f"Failed to get quote stats: {e}")
        return error_response(f"Failed to get quote stats: {str(e)}", status_code=500)


app.register_blueprint(api_bp)


if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
