"""
Twitch collector - Quart Application with TwitchIO IRC Bot
Supports !prefix commands via chat and EventSub webhooks for subs, raids, follows
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
                        success_response, error_response)
from config import Config  # noqa: E402
from services.viewer_tracker import ViewerTracker  # noqa: E402
from services.twitch_bot import TwitchBotService  # noqa: E402
from services.channel_manager import ChannelManager  # noqa: E402
from services.eventsub_handler import EventSubHandler  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
eventsub_bp = Blueprint('eventsub', __name__, url_prefix='/eventsub')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
viewer_tracker = None
twitch_bot = None
channel_manager = None
eventsub_handler = None
bot_task = None


async def _load_tracked_channels(dal) -> dict:
    """Load Twitch channels to track from database"""
    channels = {}
    try:
        # Query servers table for active Twitch channels with community mapping
        result = dal.executesql(
            """SELECT s.platform_server_id, s.platform_data, cs.community_id
               FROM servers s
               JOIN community_servers cs ON cs.platform_server_id = s.platform_server_id
               WHERE s.platform = 'twitch' AND s.is_active = true AND cs.is_active = true
            """
        )
        for row in result:
            channel_id = row[0]
            platform_data = row[1] or {}
            community_id = row[2]

            # Extract broadcaster_id from platform_data JSON
            broadcaster_id = ''
            channel_name = channel_id.lower()
            if isinstance(platform_data, dict):
                broadcaster_id = platform_data.get('broadcaster_id', '')
                if platform_data.get('channel_name'):
                    channel_name = platform_data['channel_name'].lower()

            channels[channel_name] = {
                'broadcaster_id': broadcaster_id,
                'community_id': community_id,
                'platform_server_id': channel_id
            }
        logger.info(f"Loaded {len(channels)} Twitch channels")
    except Exception as e:
        logger.warning(f"Failed to load tracked channels: {e}")
    return channels


@app.before_serving
async def startup():
    global dal, viewer_tracker, twitch_bot, channel_manager, eventsub_handler, bot_task
    logger.system("Starting twitch_module", action="startup")
    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal

    # Load channels from database
    channels = await _load_tracked_channels(dal)

    # Build channel -> community mapping
    channel_community_map = {
        name: info['community_id']
        for name, info in channels.items()
    }

    # Initialize Twitch IRC Bot if configured
    if Config.TWITCH_BOT_ENABLED and Config.TWITCH_BOT_TOKEN:
        channel_names = list(channels.keys()) if channels else []

        twitch_bot = TwitchBotService(
            token=Config.TWITCH_BOT_TOKEN,
            client_id=Config.TWITCH_CLIENT_ID,
            nick=Config.TWITCH_BOT_NICK,
            initial_channels=channel_names,
            router_url=Config.ROUTER_API_URL,
            dal=dal,
            channel_community_map=channel_community_map,
            log_level=Config.LOG_LEVEL
        )

        # Initialize channel manager for dynamic channel updates
        channel_manager = ChannelManager(
            dal=dal,
            bot=twitch_bot,
            refresh_interval=Config.CHANNEL_REFRESH_INTERVAL
        )

        # Start bot in background task
        bot_task = asyncio.create_task(_run_bot())
        logger.system("Twitch IRC bot started", result="SUCCESS")
    else:
        logger.system(
            "Twitch bot not started - TWITCH_BOT_TOKEN not configured",
            result="SKIPPED"
        )

    # Initialize EventSub handler if configured
    if Config.EVENTSUB_ENABLED and Config.EVENTSUB_SECRET:
        eventsub_handler = EventSubHandler(
            client_id=Config.TWITCH_CLIENT_ID,
            client_secret=Config.TWITCH_CLIENT_SECRET,
            eventsub_secret=Config.EVENTSUB_SECRET,
            router_url=Config.ROUTER_API_URL,
            callback_url=Config.EVENTSUB_CALLBACK_URL,
            log_level=Config.LOG_LEVEL
        )
        app.config['eventsub_handler'] = eventsub_handler
        logger.system("EventSub handler initialized", result="SUCCESS")
    else:
        logger.system(
            "EventSub not started - EVENTSUB_SECRET not configured",
            result="SKIPPED"
        )

    # Initialize viewer tracker if enabled (existing functionality)
    if Config.VIEWER_TRACKING_ENABLED and Config.HUB_API_URL and Config.SERVICE_API_KEY:
        viewer_tracker = ViewerTracker(
            hub_api_url=Config.HUB_API_URL,
            service_api_key=Config.SERVICE_API_KEY,
            twitch_client_id=Config.TWITCH_CLIENT_ID,
            twitch_access_token=Config.TWITCH_ACCESS_TOKEN,
            poll_interval=Config.VIEWER_POLL_INTERVAL,
        )
        if channels:
            await viewer_tracker.start(channels)
            logger.system("Viewer tracker started", result="SUCCESS")
        else:
            logger.info("No channels to track - viewer tracker not started")
    else:
        logger.info("Viewer tracking disabled or missing configuration")

    logger.system("twitch_module started", result="SUCCESS")


async def _run_bot():
    """Run the Twitch bot - handles connection and reconnection"""
    try:
        # Start channel manager for periodic refreshes
        if channel_manager:
            await channel_manager.start()

        # Run the bot (blocking until stopped)
        await twitch_bot.start()
    except asyncio.CancelledError:
        logger.info("Bot task cancelled")
    except Exception as e:
        logger.error(f"Bot error: {e}")


@app.after_serving
async def shutdown():
    logger.system("Shutting down twitch_module", action="shutdown")

    # Stop channel manager
    if channel_manager:
        await channel_manager.stop()
        logger.info("Channel manager stopped")

    # Stop Twitch bot
    if twitch_bot:
        await twitch_bot.stop()
        logger.info("Twitch bot stopped")

    # Cancel bot task
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            pass

    # Stop EventSub handler
    if eventsub_handler:
        await eventsub_handler.stop()
        logger.info("EventSub handler stopped")

    # Stop viewer tracker
    if viewer_tracker:
        await viewer_tracker.stop()
        logger.system("Viewer tracker stopped", result="SUCCESS")

    logger.system("twitch_module shutdown complete", result="SUCCESS")


# API Endpoints
@api_bp.route('/status')
@async_endpoint
async def status():
    bot_connected = twitch_bot is not None
    channels_count = len(channel_manager.get_all_channels()) if channel_manager else 0
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "bot_connected": bot_connected,
        "channels_count": channels_count,
        "features": {
            "prefix_commands": True,
            "eventsub": Config.EVENTSUB_ENABLED,
            "viewer_tracking": Config.VIEWER_TRACKING_ENABLED
        }
    })


@api_bp.route('/bot/channels')
@async_endpoint
async def bot_channels():
    """Get list of channels the bot is connected to"""
    if not channel_manager:
        return error_response("Bot not running", 503)
    channels = channel_manager.get_all_channels()
    return success_response({
        "channels": list(channels.keys()),
        "count": len(channels)
    })


@api_bp.route('/bot/send', methods=['POST'])
@async_endpoint
async def send_message():
    """Send a message to a Twitch channel"""
    if not twitch_bot:
        return error_response("Bot not running", 503)

    data = await request.get_json()
    channel = data.get('channel')
    message = data.get('message')

    if not channel or not message:
        return error_response("channel and message required", 400)

    await twitch_bot.send_message(channel, message)
    return success_response({"sent": True})


# EventSub Webhook Endpoint
@eventsub_bp.route('/webhook', methods=['POST'])
async def eventsub_webhook():
    """Handle Twitch EventSub webhooks"""
    if not eventsub_handler:
        return {"error": "EventSub not configured"}, 503

    # Get raw body for signature verification
    body = await request.get_data()
    body_json = await request.get_json()
    headers = dict(request.headers)

    result = await eventsub_handler.handle_webhook(headers, body, body_json)

    # Handle challenge response (subscription verification)
    if 'challenge' in result:
        return result['challenge'], 200, {'Content-Type': 'text/plain'}

    # Handle errors
    if 'error' in result:
        return result, 403

    return result, 200


app.register_blueprint(api_bp)
app.register_blueprint(eventsub_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
