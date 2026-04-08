"""
Security Core Module - Main Application

Provides spam detection, content filtering, warnings, and cross-platform moderation.
"""
import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'libs'))

from quart import Quart, Blueprint, request, jsonify
from flask_core import (
    setup_aaa_logging,
    init_database,
    success_response,
    error_response,
    create_health_blueprint,
)
from config import Config

# Create Quart app
app = Quart(__name__)

# Health blueprint
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

# API blueprints
api_bp = Blueprint('api', __name__, url_prefix='/api/v1/security')
internal_bp = Blueprint('internal', __name__, url_prefix='/api/v1/internal')

# Logger setup
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

# Global service instances
dal = None
security_service = None
spam_detector = None
content_filter = None
warning_manager = None


@app.before_serving
async def startup():
    """Initialize services on startup."""
    global dal, security_service, spam_detector, content_filter, warning_manager

    logger.system("Starting security-core module", action="startup")

    try:
        # Initialize database
        dal = init_database(Config.DATABASE_URL)
        app.config['dal'] = dal
        logger.system("Database initialized", result="SUCCESS")

        # Import services
        from services.security_service import SecurityService
        from services.spam_detector import SpamDetector
        from services.content_filter import ContentFilter
        from services.warning_manager import WarningManager

        # Initialize services
        security_service = SecurityService(dal, logger)
        spam_detector = SpamDetector(dal, logger)
        content_filter = ContentFilter(dal, logger)
        warning_manager = WarningManager(dal, logger)

        logger.system("Security core module started", result="SUCCESS")

    except Exception as e:
        logger.error(f"Startup failed: {e}", action="startup", result="FAILED")
        raise


@app.after_serving
async def shutdown():
    """Cleanup on shutdown."""
    logger.system("Shutting down security-core module", action="shutdown")
    logger.system("Security core module shutdown complete", result="SUCCESS")


# ============================================================================
# PUBLIC API ENDPOINTS
# ============================================================================

@api_bp.route('/status', methods=['GET'])
async def get_status():
    """Get module status."""
    return jsonify(success_response({
        'module': Config.MODULE_NAME,
        'version': Config.MODULE_VERSION,
        'status': 'healthy'
    }))


@api_bp.route('/<int:community_id>/config', methods=['GET'])
async def get_config(community_id: int):
    """Get security configuration for community."""
    try:
        config = await security_service.get_config(community_id)
        return jsonify(success_response(config))
    except Exception as e:
        logger.error(f"Failed to get config: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/config', methods=['PUT'])
async def update_config(community_id: int):
    """Update security configuration for community."""
    try:
        data = await request.get_json()
        config = await security_service.update_config(community_id, data)
        return jsonify(success_response(config))
    except Exception as e:
        logger.error(f"Failed to update config: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/warnings', methods=['GET'])
async def get_warnings(community_id: int):
    """
    List all warnings for community.

    Query params:
    - status: active, expired, all (default: active)
    - page: page number (default: 1)
    - limit: results per page (default: 25)
    """
    try:
        status = request.args.get('status', 'active')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 25))

        warnings = await warning_manager.get_warnings(community_id, status, page, limit)
        return jsonify(success_response(warnings))
    except Exception as e:
        logger.error(f"Failed to get warnings: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/warnings', methods=['POST'])
async def issue_manual_warning(community_id: int):
    """
    Issue manual warning.

    Expected payload:
    {
        "platform": str,
        "platform_user_id": str,
        "warning_reason": str,
        "issued_by": int (hub_user_id)
    }
    """
    try:
        data = await request.get_json()
        warning = await warning_manager.issue_manual_warning(
            community_id=community_id,
            platform=data['platform'],
            platform_user_id=data['platform_user_id'],
            warning_reason=data['warning_reason'],
            issued_by=data.get('issued_by')
        )
        return jsonify(success_response(warning))
    except Exception as e:
        logger.error(f"Failed to issue warning: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/warnings/<int:warning_id>', methods=['DELETE'])
async def revoke_warning(community_id: int, warning_id: int):
    """
    Revoke warning.

    Expected payload:
    {
        "revoked_by": int (hub_user_id),
        "revoke_reason": str
    }
    """
    try:
        data = await request.get_json()
        result = await warning_manager.revoke_warning(
            warning_id=warning_id,
            revoked_by=data.get('revoked_by'),
            revoke_reason=data.get('revoke_reason')
        )
        return jsonify(success_response(result))
    except Exception as e:
        logger.error(f"Failed to revoke warning: {e}", warning_id=warning_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/filter-matches', methods=['GET'])
async def get_filter_matches(community_id: int):
    """
    View filter match log.

    Query params:
    - page: page number (default: 1)
    - limit: results per page (default: 50)
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))

        matches = await content_filter.get_filter_matches(community_id, page, limit)
        return jsonify(success_response(matches))
    except Exception as e:
        logger.error(f"Failed to get filter matches: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/blocked-words', methods=['POST'])
async def add_blocked_words(community_id: int):
    """
    Add blocked words.

    Expected payload:
    {
        "words": ["word1", "word2", ...]
    }
    """
    try:
        data = await request.get_json()
        result = await content_filter.add_blocked_words(community_id, data['words'])
        return jsonify(success_response(result))
    except Exception as e:
        logger.error(f"Failed to add blocked words: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/blocked-words', methods=['DELETE'])
async def remove_blocked_words(community_id: int):
    """
    Remove blocked words.

    Expected payload:
    {
        "words": ["word1", "word2", ...]
    }
    """
    try:
        data = await request.get_json()
        result = await content_filter.remove_blocked_words(community_id, data['words'])
        return jsonify(success_response(result))
    except Exception as e:
        logger.error(f"Failed to remove blocked words: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


@api_bp.route('/<int:community_id>/moderation-log', methods=['GET'])
async def get_moderation_log(community_id: int):
    """
    View moderation actions log.

    Query params:
    - page: page number (default: 1)
    - limit: results per page (default: 50)
    """
    try:
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 50))

        actions = await security_service.get_moderation_log(community_id, page, limit)
        return jsonify(success_response(actions))
    except Exception as e:
        logger.error(f"Failed to get moderation log: {e}", community_id=community_id)
        return jsonify(error_response(str(e), 500))


# ============================================================================
# INTERNAL API ENDPOINTS (Service-to-Service)
# ============================================================================

@internal_bp.route('/check', methods=['POST'])
async def check_message():
    """
    Check message against filters (real-time).

    Expected payload:
    {
        "community_id": int,
        "platform": str,
        "platform_user_id": str,
        "message": str,
        "metadata": {}
    }

    Returns:
    {
        "allowed": bool,
        "blocked_reason": str (if blocked),
        "action_taken": str
    }
    """
    try:
        data = await request.get_json()

        # Check spam
        is_spam = await spam_detector.check_spam(
            community_id=data['community_id'],
            platform=data['platform'],
            platform_user_id=data['platform_user_id']
        )

        # Check content filter
        is_filtered, matched_pattern = await content_filter.check_message(
            community_id=data['community_id'],
            message=data['message']
        )

        # Determine action
        if is_spam:
            return jsonify(success_response({
                'allowed': False,
                'blocked_reason': 'spam_detected',
                'action_taken': 'warn'
            }))

        if is_filtered:
            return jsonify(success_response({
                'allowed': False,
                'blocked_reason': 'content_filtered',
                'matched_pattern': matched_pattern,
                'action_taken': 'delete'
            }))

        return jsonify(success_response({
            'allowed': True
        }))

    except Exception as e:
        logger.error(f"Failed to check message: {e}")
        return jsonify(error_response(str(e), 500))


@internal_bp.route('/warn', methods=['POST'])
async def issue_automated_warning():
    """
    Issue automated warning.

    Expected payload:
    {
        "community_id": int,
        "platform": str,
        "platform_user_id": str,
        "warning_type": str,
        "warning_reason": str,
        "trigger_message": str
    }
    """
    try:
        data = await request.get_json()
        warning = await warning_manager.issue_automated_warning(
            community_id=data['community_id'],
            platform=data['platform'],
            platform_user_id=data['platform_user_id'],
            warning_type=data['warning_type'],
            warning_reason=data['warning_reason'],
            trigger_message=data.get('trigger_message')
        )
        return jsonify(success_response(warning))
    except Exception as e:
        logger.error(f"Failed to issue automated warning: {e}")
        return jsonify(error_response(str(e), 500))


@internal_bp.route('/sync-action', methods=['POST'])
async def sync_moderation_action():
    """
    Sync moderation action across platforms.

    Expected payload:
    {
        "community_id": int,
        "platform": str,
        "platform_user_id": str,
        "action_type": str,
        "action_reason": str,
        "moderator_id": int,
        "sync_to_platforms": []
    }
    """
    try:
        data = await request.get_json()
        result = await security_service.sync_moderation_action(
            community_id=data['community_id'],
            platform=data['platform'],
            platform_user_id=data['platform_user_id'],
            action_type=data['action_type'],
            action_reason=data.get('action_reason'),
            moderator_id=data.get('moderator_id'),
            sync_to_platforms=data.get('sync_to_platforms', [])
        )
        return jsonify(success_response(result))
    except Exception as e:
        logger.error(f"Failed to sync moderation action: {e}")
        return jsonify(error_response(str(e), 500))


# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(internal_bp)


if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    config.workers = 4

    logger.system(f"Starting security-core on port {Config.MODULE_PORT}")
    asyncio.run(hypercorn.asyncio.serve(app, config))
