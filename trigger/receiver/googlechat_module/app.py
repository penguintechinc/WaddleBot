"""
Google Chat receiver - Quart Application
Supports slash commands, card interactions, and message relay
"""
import asyncio
import os
import sys

from quart import Blueprint, Quart, request

# Setup path for shared libraries
sys.path.insert(0,
                os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             'libs'))

from flask_core import (async_endpoint, create_health_blueprint,  # noqa: E402
                        init_database, setup_aaa_logging,
                        success_response)
from config import Config  # noqa: E402
from services.googlechat_bot import GoogleChatBotService  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
googlechat_bp = Blueprint('googlechat', __name__, url_prefix='/googlechat')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
googlechat_bot = None


@app.before_serving
async def startup():
    global dal, googlechat_bot
    logger.system("Starting googlechat_module", action="startup")

    # Validate configuration
    errors, warnings = Config.validate()
    if errors:
        logger.error(f"Configuration errors: {errors}")
        raise RuntimeError(f"Configuration errors: {errors}")

    if warnings:
        for warning in warnings:
            logger.warning(warning)

    # Initialize database
    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal

    # Initialize Google Chat Bot service if configured
    if Config.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY:
        googlechat_bot = GoogleChatBotService(
            service_account_key=Config.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY,
            project_id=Config.GOOGLE_CHAT_PROJECT_ID,
            router_url=Config.ROUTER_API_URL,
            dal=dal,
            log_level=Config.LOG_LEVEL
        )

        app.config['googlechat_bot'] = googlechat_bot
        logger.system("Google Chat service initialized", result="SUCCESS")
    else:
        logger.system(
            "Google Chat not started - GOOGLE_CHAT_SERVICE_ACCOUNT_KEY not configured",
            result="SKIPPED"
        )

    logger.system("googlechat_module started", result="SUCCESS")


@app.after_serving
async def shutdown():
    global googlechat_bot
    logger.system("Shutting down googlechat_module", action="shutdown")

    if googlechat_bot:
        await googlechat_bot.stop()
        logger.system("Google Chat service stopped", result="SUCCESS")


@api_bp.route('/status')
@async_endpoint
async def status():
    connected = googlechat_bot is not None
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "googlechat_connected": connected,
        "features": {
            "slash_commands": True,
            "card_interactions": True,
            "space_management": True,
            "card_v2": True
        }
    })


# Google Chat event routes
@googlechat_bp.route('/events', methods=['POST'])
async def googlechat_events():
    """Handle Google Chat Events API"""
    if not googlechat_bot:
        return {"error": "Google Chat not configured"}, 503

    try:
        data = await request.get_json()
        response = await googlechat_bot.handle_event(data)
        return response
    except Exception as e:
        logger.error(f"Error handling Google Chat event: {e}")
        return {"error": "Failed to process event"}, 500


internal_bp = Blueprint('internal', __name__, url_prefix='/internal')


@internal_bp.route('/relay', methods=['POST'])
async def internal_relay():
    """Receive relayed messages from hub and send to Google Chat spaces"""
    from quart import jsonify
    if not googlechat_bot:
        return jsonify({"success": False, "error": "Google Chat not configured"}), 503

    data = await request.get_json()
    space_id = data.get('platformChannelId')
    content = data.get('content', {})
    author = data.get('author', {})
    message_type = data.get('messageType', 'message')

    if not space_id:
        return jsonify({"success": False, "error": "platformChannelId required"}), 400

    ok = await googlechat_bot.send_to_space(space_id, content, author, message_type)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Failed to send"}), 500


app.register_blueprint(internal_bp)
app.register_blueprint(api_bp)
app.register_blueprint(googlechat_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
