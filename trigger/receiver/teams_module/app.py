"""
Teams collector - Quart Application with Microsoft Bot Framework
Supports messages, slash commands, and adaptive cards
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
from services.teams_bot import TeamsBotService  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
teams_bp = Blueprint('teams', __name__, url_prefix='/teams')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
teams_bot = None


@app.before_serving
async def startup():
    global dal, teams_bot
    logger.system("Starting teams_module", action="startup")

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

    # Initialize Teams Bot service if configured
    if Config.TEAMS_APP_ID and Config.TEAMS_APP_PASSWORD:
        teams_bot = TeamsBotService(
            app_id=Config.TEAMS_APP_ID,
            app_password=Config.TEAMS_APP_PASSWORD,
            tenant_id=Config.TEAMS_TENANT_ID,
            router_url=Config.ROUTER_API_URL,
            dal=dal,
            log_level=Config.LOG_LEVEL
        )

        # Start the bot service
        await teams_bot.start()
        app.config['teams_bot'] = teams_bot

        logger.system("Teams Bot service initialized", result="SUCCESS")
    else:
        logger.system(
            "Teams not started - TEAMS_APP_ID or TEAMS_APP_PASSWORD not configured",
            result="SKIPPED"
        )

    logger.system("teams_module started", result="SUCCESS")


@app.after_serving
async def shutdown():
    global teams_bot
    logger.system("Shutting down teams_module", action="shutdown")

    if teams_bot:
        await teams_bot.stop()
        logger.system("Teams service stopped", result="SUCCESS")


@api_bp.route('/status')
@async_endpoint
async def status():
    connected = teams_bot is not None
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "teams_connected": connected,
        "features": {
            "messages": True,
            "commands": True,
            "adaptive_cards": True,
            "relay": True
        }
    })


# Teams Bot Framework webhook - handles all incoming activities
@teams_bp.route('/api/messages', methods=['POST'])
async def teams_messages():
    """Handle Microsoft Bot Framework webhook for Teams"""
    if not teams_bot:
        return {"error": "Teams not configured"}, 503

    try:
        # Parse incoming activity
        from botbuilder.schema import Activity
        body = await request.get_json()

        if not body:
            return {"error": "No activity provided"}, 400

        activity = Activity().deserialize(body)

        # Process the activity
        await teams_bot.process_activity(activity)

        return {"success": True}, 200

    except Exception as e:
        logger.error(f"Teams webhook processing failed: {e}", action="webhook_error")
        return {"error": str(e)}, 500


internal_bp = Blueprint('internal', __name__, url_prefix='/internal')


@internal_bp.route('/relay', methods=['POST'])
async def internal_relay():
    """Receive relayed messages from hub and send to Teams channels"""
    from quart import jsonify
    if not teams_bot:
        return jsonify({"success": False, "error": "Teams not configured"}), 503

    data = await request.get_json()
    channel_id = data.get('platformChannelId')
    team_id = data.get('platformServerId')
    content = data.get('content', {})
    author = data.get('author', {})
    message_type = data.get('messageType', 'message')

    if not channel_id:
        return jsonify({"success": False, "error": "platformChannelId required"}), 400

    ok = await teams_bot.send_to_channel(
        channel_id=channel_id,
        team_id=team_id or '',
        content=content,
        author=author,
        message_type=message_type
    )
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Failed to send"}), 500


app.register_blueprint(internal_bp)
app.register_blueprint(api_bp)
app.register_blueprint(teams_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
