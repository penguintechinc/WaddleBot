"""
LFG (Looking for Group) Interaction Module

Manages group-finding posts: create, join, leave, cancel, and expire.
"""
import asyncio
import os
import sys

# Add libs path for flask_core
sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'libs',
    ),
)

from quart import Blueprint, Quart, request  # noqa: E402
from flask_core import (  # noqa: E402
    async_endpoint,
    create_health_blueprint,
    error_response,
    init_database,
    setup_aaa_logging,
    success_response,
)

from config import Config  # noqa: E402
from services.lfg_service import LfgService  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('lfg_api', __name__, url_prefix='/api/v1/lfg')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
lfg_service = None


@app.before_serving
async def startup():
    global dal, lfg_service
    logger.system("Starting lfg_interaction_module", action="startup")

    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal

    lfg_service = LfgService(dal, Config)

    logger.system("lfg_interaction_module started", result="SUCCESS")


# =====================================================
# LFG POST ENDPOINTS
# =====================================================


@api_bp.route('/posts', methods=['POST'])
@async_endpoint
async def create_post():
    """
    Create a new LFG post.

    Request JSON:
    {
        "community_id": 123,
        "user_id": "456",
        "platform": "discord",
        "game": "Destiny 2",
        "activity": "Raid - King's Fall",
        "role": "DPS",
        "rank_or_level": "1810 Power",
        "player_count_needed": 3,
        "message": "Need 3 more for KF, know the mechanics"
    }
    """
    try:
        data = await request.get_json()

        community_id = data.get('community_id')
        user_id = data.get('user_id')
        platform = data.get('platform')
        game = data.get('game')

        if not all([community_id, user_id, platform, game]):
            return error_response(
                "community_id, user_id, platform, and game are required",
                status_code=400,
            )

        logger.audit(
            action="create_lfg_post",
            community=community_id,
            user=user_id,
            game=game,
            result="STARTED",
        )

        result = await lfg_service.create_post(
            community_id=community_id,
            user_id=user_id,
            platform=platform,
            game=game,
            activity=data.get('activity'),
            role=data.get('role'),
            rank_or_level=data.get('rank_or_level'),
            player_count_needed=data.get('player_count_needed', 1),
            message=data.get('message'),
            platform_message_id=data.get('platform_message_id'),
        )

        if not result.get('success'):
            logger.audit(
                action="create_lfg_post",
                community=community_id,
                user=user_id,
                result="FAILED",
                error=result.get('error'),
            )
            return error_response(result.get('error'), status_code=400)

        logger.audit(
            action="create_lfg_post",
            community=community_id,
            user=user_id,
            game=game,
            result="SUCCESS",
        )

        return success_response(result)

    except Exception as e:
        logger.error("Failed to create LFG post: %s", e)
        return error_response(str(e), status_code=500)


@api_bp.route('/posts/<int:community_id>', methods=['GET'])
@async_endpoint
async def get_active_posts(community_id: int):
    """
    List active LFG posts for a community.

    Query params:
    - game: Optional game name filter
    """
    try:
        game = request.args.get('game')

        posts = await lfg_service.get_active_posts(community_id, game=game)

        return success_response({
            'posts': posts,
            'count': len(posts),
        })

    except Exception as e:
        logger.error("Failed to get active LFG posts: %s", e)
        return error_response(str(e), status_code=500)


@api_bp.route('/posts/<int:post_id>/join', methods=['POST'])
@async_endpoint
async def join_post(post_id: int):
    """
    Join an LFG post.

    Request JSON:
    {
        "user_id": "456",
        "platform": "discord",
        "display_name": "PlayerOne"
    }
    """
    try:
        data = await request.get_json()

        user_id = data.get('user_id')
        platform = data.get('platform')

        if not all([user_id, platform]):
            return error_response(
                "user_id and platform are required",
                status_code=400,
            )

        result = await lfg_service.join_post(
            post_id=post_id,
            user_id=user_id,
            platform=platform,
            display_name=data.get('display_name'),
        )

        if not result.get('success'):
            return error_response(result.get('error'), status_code=400)

        return success_response(result)

    except Exception as e:
        logger.error("Failed to join LFG post: %s", e)
        return error_response(str(e), status_code=500)


@api_bp.route('/posts/<int:post_id>/join', methods=['DELETE'])
@async_endpoint
async def leave_post(post_id: int):
    """
    Leave an LFG post.

    Request JSON:
    {
        "user_id": "456"
    }
    """
    try:
        data = await request.get_json()

        user_id = data.get('user_id')

        if not user_id:
            return error_response(
                "user_id is required", status_code=400
            )

        result = await lfg_service.leave_post(
            post_id=post_id, user_id=user_id
        )

        if not result.get('success'):
            return error_response(result.get('error'), status_code=400)

        return success_response(result)

    except Exception as e:
        logger.error("Failed to leave LFG post: %s", e)
        return error_response(str(e), status_code=500)


@api_bp.route('/posts/<int:post_id>', methods=['DELETE'])
@async_endpoint
async def cancel_post(post_id: int):
    """
    Cancel an LFG post. Only the creator can cancel.

    Request JSON:
    {
        "user_id": "456"
    }
    """
    try:
        data = await request.get_json()

        user_id = data.get('user_id')

        if not user_id:
            return error_response(
                "user_id is required", status_code=400
            )

        result = await lfg_service.cancel_post(
            post_id=post_id, user_id=user_id
        )

        if not result.get('success'):
            return error_response(result.get('error'), status_code=400)

        return success_response(result)

    except Exception as e:
        logger.error("Failed to cancel LFG post: %s", e)
        return error_response(str(e), status_code=500)


@api_bp.route('/expire', methods=['POST'])
@async_endpoint
async def expire_posts():
    """
    Expire old LFG posts (cron endpoint).

    Called periodically to clean up posts past their expiry time.
    """
    try:
        expired_count = await lfg_service.expire_old_posts()

        return success_response({
            'expired_count': expired_count,
        })

    except Exception as e:
        logger.error("Failed to expire LFG posts: %s", e)
        return error_response(str(e), status_code=500)


# =====================================================
# STATUS ENDPOINT
# =====================================================


status_bp = Blueprint('status', __name__, url_prefix='/api/v1')


@status_bp.route('/status')
@async_endpoint
async def status():
    """Module status endpoint"""
    return success_response({
        'status': 'operational',
        'module': Config.MODULE_NAME,
        'version': Config.MODULE_VERSION,
    })


app.register_blueprint(api_bp)
app.register_blueprint(status_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
