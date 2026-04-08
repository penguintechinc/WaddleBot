"""
Slack collector - Quart Application with Slack Bolt
Supports slash commands (/waddlebot), prefix commands (!), modals, and buttons
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
from services.slack_bolt_app import SlackBoltService  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
slack_bp = Blueprint('slack', __name__, url_prefix='/slack')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
slack_bolt = None
slack_handler = None


@app.before_serving
async def startup():
    global dal, slack_bolt, slack_handler
    logger.system("Starting slack_module", action="startup")

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

    # Initialize Slack Bolt service if configured
    if Config.SLACK_BOT_TOKEN and Config.SLACK_SIGNING_SECRET:
        slack_bolt = SlackBoltService(
            bot_token=Config.SLACK_BOT_TOKEN,
            signing_secret=Config.SLACK_SIGNING_SECRET,
            app_token=Config.SLACK_APP_TOKEN,
            router_url=Config.ROUTER_API_URL,
            dal=dal,
            use_socket_mode=Config.USE_SOCKET_MODE,
            log_level=Config.LOG_LEVEL
        )

        # Get Quart handler for HTTP mode
        slack_handler = slack_bolt.get_quart_handler()
        app.config['slack_bolt'] = slack_bolt

        # Start Socket Mode if configured (for development)
        if Config.USE_SOCKET_MODE:
            asyncio.create_task(slack_bolt.start_socket_mode())
            logger.system("Slack Socket Mode started", result="SUCCESS")
        else:
            logger.system("Slack HTTP mode ready", result="SUCCESS")
    else:
        logger.system(
            "Slack not started - SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET not configured",
            result="SKIPPED"
        )

    logger.system("slack_module started", result="SUCCESS")


@app.after_serving
async def shutdown():
    global slack_bolt
    logger.system("Shutting down slack_module", action="shutdown")

    if slack_bolt:
        await slack_bolt.stop()
        logger.system("Slack service stopped", result="SUCCESS")


@api_bp.route('/status')
@async_endpoint
async def status():
    connected = slack_bolt is not None
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "slack_connected": connected,
        "mode": "socket" if Config.USE_SOCKET_MODE else "http",
        "features": {
            "slash_commands": True,
            "prefix_commands": True,
            "modals": True,
            "buttons": True,
            "block_kit": True
        }
    })


# Slack event routes (for HTTP mode)
@slack_bp.route('/events', methods=['POST'])
async def slack_events():
    """Handle Slack Events API"""
    if not slack_handler:
        return {"error": "Slack not configured"}, 503
    return await slack_handler.handle(request)


@slack_bp.route('/commands', methods=['POST'])
async def slack_commands():
    """Handle Slack slash commands"""
    if not slack_handler:
        return {"error": "Slack not configured"}, 503
    return await slack_handler.handle(request)


@slack_bp.route('/actions', methods=['POST'])
async def slack_actions():
    """Handle Slack interactive components"""
    if not slack_handler:
        return {"error": "Slack not configured"}, 503
    return await slack_handler.handle(request)


@slack_bp.route('/shortcuts', methods=['POST'])
async def slack_shortcuts():
    """Handle Slack shortcuts"""
    if not slack_handler:
        return {"error": "Slack not configured"}, 503
    return await slack_handler.handle(request)


internal_bp = Blueprint('internal', __name__, url_prefix='/internal')


@internal_bp.route('/relay', methods=['POST'])
async def internal_relay():
    """Receive relayed messages from hub and send to Slack channels"""
    from quart import jsonify
    if not slack_bolt:
        return jsonify({"success": False, "error": "Slack not configured"}), 503

    data = await request.get_json()
    channel_id = data.get('platformChannelId')
    content = data.get('content', {})
    author = data.get('author', {})
    message_type = data.get('messageType', 'message')

    if not channel_id:
        return jsonify({"success": False, "error": "platformChannelId required"}), 400

    ok = await slack_bolt.send_to_channel(channel_id, content, author, message_type)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Failed to send"}), 500


app.register_blueprint(internal_bp)
app.register_blueprint(api_bp)
app.register_blueprint(slack_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
