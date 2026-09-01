"""
Mattermost receiver - Quart Application with Mattermost Driver
Supports slash commands, chat messages, and webhook integrations
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
from services.mattermost_bot import MattermostBotService  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
mattermost_bp = Blueprint('mattermost', __name__, url_prefix='/mattermost')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
mattermost_bot = None


@app.before_serving
async def startup():
    global dal, mattermost_bot
    logger.system("Starting mattermost_module", action="startup")

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

    # Load credentials from database if available
    Config.load_credentials_from_db(dal)

    # Initialize Mattermost Bot service if configured
    if Config.MATTERMOST_URL and Config.MATTERMOST_BOT_TOKEN:
        mattermost_bot = MattermostBotService(
            mattermost_url=Config.MATTERMOST_URL,
            bot_token=Config.MATTERMOST_BOT_TOKEN,
            webhook_secret=Config.MATTERMOST_WEBHOOK_SECRET,
            router_url=Config.ROUTER_API_URL,
            dal=dal,
            log_level=Config.LOG_LEVEL
        )

        app.config['mattermost_bot'] = mattermost_bot

        # Start the bot service (WebSocket listener)
        asyncio.create_task(mattermost_bot.start())
        logger.system("Mattermost bot service started", result="SUCCESS")
    else:
        logger.system(
            "Mattermost not started - MATTERMOST_URL or MATTERMOST_BOT_TOKEN not configured",
            result="SKIPPED"
        )

    logger.system("mattermost_module started", result="SUCCESS")


@app.after_serving
async def shutdown():
    global mattermost_bot
    logger.system("Shutting down mattermost_module", action="shutdown")

    if mattermost_bot:
        await mattermost_bot.stop()
        logger.system("Mattermost service stopped", result="SUCCESS")


@api_bp.route('/status')
@async_endpoint
async def status():
    connected = mattermost_bot is not None
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "mattermost_connected": connected,
        "features": {
            "slash_commands": True,
            "chat_messages": True,
            "webhooks": True,
            "websocket_events": True
        }
    })


# Mattermost event routes
@mattermost_bp.route('/events', methods=['POST'])
async def mattermost_events():
    """Handle Mattermost webhook events"""
    if not mattermost_bot:
        return {"error": "Mattermost not configured"}, 503

    data = await request.get_json()

    # Verify webhook signature
    if not mattermost_bot.verify_webhook_signature(request.headers, data):
        logger.warning("Invalid webhook signature", action="webhook_verify")
        return {"error": "Invalid signature"}, 401

    # Process the event
    await mattermost_bot.handle_webhook_event(data)
    return {"success": True}, 200


@mattermost_bp.route('/commands', methods=['POST'])
async def mattermost_commands():
    """Handle Mattermost slash commands"""
    if not mattermost_bot:
        return {"error": "Mattermost not configured"}, 503

    data = await request.get_json()

    # Verify webhook signature
    if not mattermost_bot.verify_webhook_signature(request.headers, data):
        logger.warning("Invalid webhook signature", action="command_verify")
        return {"error": "Invalid signature"}, 401

    response = await mattermost_bot.handle_slash_command(data)
    return response or {"success": True}, 200


internal_bp = Blueprint('internal', __name__, url_prefix='/internal')


@internal_bp.route('/relay', methods=['POST'])
async def internal_relay():
    """Receive relayed messages from hub and send to Mattermost channels"""
    from quart import jsonify
    if not mattermost_bot:
        return jsonify({"success": False, "error": "Mattermost not configured"}), 503

    data = await request.get_json()
    channel_id = data.get('platformChannelId')
    content = data.get('content', {})
    author = data.get('author', {})
    message_type = data.get('messageType', 'message')

    if not channel_id:
        return jsonify({"success": False, "error": "platformChannelId required"}), 400

    ok = await mattermost_bot.send_to_channel(channel_id, content, author, message_type)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Failed to send"}), 500


app.register_blueprint(internal_bp)
app.register_blueprint(api_bp)
app.register_blueprint(mattermost_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
