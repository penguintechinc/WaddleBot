"""
Discord collector - Quart Application with py-cord Bot
Supports slash commands (/), prefix commands (!), modals, buttons, and selects
"""
import asyncio
import os
import sys

from quart import Quart, Blueprint, request, jsonify

from flask_core import (  # noqa: E402
    setup_aaa_logging, init_database, async_endpoint, success_response,
    create_health_blueprint
)
from config import Config  # noqa: E402
from services.discord_bot import DiscordBotService  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs'))

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
discord_bot = None


@app.before_serving
async def startup():
    global dal, discord_bot
    logger.system("Starting discord_module", action="startup")

    # Initialize database
    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal

    # Initialize and start Discord bot if token is configured
    if Config.DISCORD_BOT_TOKEN:
        discord_bot = DiscordBotService(
            bot_token=Config.DISCORD_BOT_TOKEN,
            application_id=Config.DISCORD_APPLICATION_ID,
            router_url=Config.ROUTER_API_URL,
            dal=dal,
            redis_url=Config.REDIS_URL if Config.REDIS_URL else None,
            log_level=Config.LOG_LEVEL
        )
        await discord_bot.start()
        app.config['discord_bot'] = discord_bot
        logger.system("Discord bot started", result="SUCCESS")
    else:
        logger.system(
            "Discord bot not started - DISCORD_BOT_TOKEN not configured",
            result="SKIPPED"
        )

    logger.system("discord_module started", result="SUCCESS")


@app.after_serving
async def shutdown():
    global discord_bot
    logger.system("Shutting down discord_module", action="shutdown")

    if discord_bot:
        await discord_bot.stop()
        logger.system("Discord bot stopped", result="SUCCESS")


@api_bp.route('/status')
@async_endpoint
async def status():
    bot_status = "connected" if discord_bot and discord_bot.bot.is_ready() else "disconnected"
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "bot_status": bot_status,
        "features": {
            "slash_commands": True,
            "prefix_commands": True,
            "modals": True,
            "buttons": True,
            "select_menus": True,
            "autocomplete": True
        }
    })


@api_bp.route('/bot/guilds')
@async_endpoint
async def bot_guilds():
    """Get list of guilds the bot is in"""
    if not discord_bot or not discord_bot.bot.is_ready():
        return success_response({"guilds": [], "error": "Bot not connected"})

    guilds = [
        {"id": str(g.id), "name": g.name, "member_count": g.member_count}
        for g in discord_bot.bot.guilds
    ]
    return success_response({"guilds": guilds, "count": len(guilds)})


internal_bp = Blueprint('internal', __name__, url_prefix='/internal')


@internal_bp.route('/relay', methods=['POST'])
async def internal_relay():
    """Receive relayed messages from hub and send to Discord channels"""
    if not discord_bot or not discord_bot.bot.is_ready():
        return jsonify({"success": False, "error": "Bot not connected"}), 503

    data = await request.get_json()
    channel_id = data.get('platformChannelId')
    content = data.get('content', {})
    author = data.get('author', {})
    message_type = data.get('messageType', 'message')

    if not channel_id:
        return jsonify({"success": False, "error": "platformChannelId required"}), 400

    ok = await discord_bot.send_to_channel(channel_id, content, author, message_type)
    if ok:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Failed to send"}), 500


app.register_blueprint(internal_bp)
app.register_blueprint(api_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
