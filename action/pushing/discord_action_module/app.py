"""
Discord Action Module - Main Application

Stateless, clusterable module for pushing actions to Discord
Receives tasks via gRPC from processor/router
Also provides REST API for third-party integration
"""

import asyncio
import logging
import logging.handlers
import sys
from concurrent import futures
from datetime import datetime, timedelta

import grpc
import jwt
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig
from proto import discord_action_pb2_grpc
from pydal import DAL
from quart import Quart, jsonify, request

from config import Config
from services.discord_service import DiscordService
from services.grpc_auth_interceptor import AuthInterceptor
from services.grpc_handler import DiscordActionServicer

# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format="[%(asctime)s] %(levelname)s %(name)s:%(lineno)d - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            f"{Config.LOG_DIR}/{Config.MODULE_NAME}.log",
            maxBytes=10485760,
            backupCount=5,
        ),
    ],
)
logger = logging.getLogger(__name__)

# Initialize Quart app
app = Quart(__name__)

# Initialize database
db = DAL(Config.DATABASE_URL, folder=None, pool_size=10, migrate_enabled=False)

# Initialize Discord service
discord_service = DiscordService(db)


def verify_jwt(token: str) -> tuple[bool, dict | str]:
    """
    Verify JWT token

    Args:
        token: JWT token string

    Returns:
        Tuple of (valid, payload_or_error)
    """
    try:
        payload = jwt.decode(
            token, Config.MODULE_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM]
        )
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, "Token expired"
    except jwt.InvalidTokenError as e:
        return False, f"Invalid token: {str(e)}"


def check_credentials() -> tuple[bool, dict | None]:
    """
    Check if required credentials are configured for API calls

    Returns:
        Tuple of (is_configured, error_response_or_none)
    """
    if not Config.DISCORD_BOT_TOKEN:
        return False, jsonify({"error": "Discord credentials not configured"}), 503
    return True, None


def require_auth(f):
    """Decorator to require JWT authentication"""

    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid authorization header"}), 401

        token = auth_header[7:]  # Remove "Bearer " prefix
        valid, result = verify_jwt(token)

        if not valid:
            return jsonify({"error": result}), 401

        return await f(*args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


# REST API Endpoints


@app.route("/health", methods=["GET"])
async def health_check():
    """Health check endpoint"""
    try:
        # Check database
        db.executesql("SELECT 1")

        return jsonify(
            {
                "status": "healthy",
                "module": Config.MODULE_NAME,
                "version": Config.MODULE_VERSION,
                "timestamp": datetime.utcnow().isoformat(),
                "config": Config.get_summary(),
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 503


@app.route("/api/v1/token", methods=["POST"])
async def generate_token():
    """
    Generate JWT token for authentication

    Request body:
    {
        "client_id": "string",
        "client_secret": "string"
    }
    """
    data = await request.get_json()
    client_id = data.get("client_id")
    client_secret = data.get("client_secret")

    # Simple validation - in production, verify against database
    if not client_id or not client_secret:
        return jsonify({"error": "Missing client_id or client_secret"}), 400

    # Generate token
    payload = {
        "client_id": client_id,
        "exp": datetime.utcnow() + timedelta(seconds=Config.JWT_EXPIRATION_SECONDS),
        "iat": datetime.utcnow(),
    }
    token = jwt.encode(payload, Config.MODULE_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)

    return jsonify({"token": token, "expires_in": Config.JWT_EXPIRATION_SECONDS})


@app.route("/api/v1/message", methods=["POST"])
@require_auth
async def send_message_rest():
    """
    Send message to Discord channel

    Request body:
    {
        "channel_id": "string",
        "content": "string",
        "embed": {...}  // optional
    }
    """
    # Check if Discord credentials are configured
    configured, error_response = check_credentials()
    if not configured:
        return error_response

    data = await request.get_json()
    channel_id = data.get("channel_id")
    content = data.get("content")
    embed = data.get("embed")

    if not channel_id or not content:
        return jsonify({"error": "Missing channel_id or content"}), 400

    success, message_id, error = await discord_service.send_message(
        channel_id, content, embed
    )

    if success:
        return jsonify({"success": True, "message_id": message_id})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/embed", methods=["POST"])
@require_auth
async def send_embed_rest():
    """Send embed to Discord channel"""
    data = await request.get_json()
    channel_id = data.get("channel_id")
    embed = data.get("embed")

    if not channel_id or not embed:
        return jsonify({"error": "Missing channel_id or embed"}), 400

    success, message_id, error = await discord_service.send_embed(channel_id, embed)

    if success:
        return jsonify({"success": True, "message_id": message_id})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/reaction", methods=["POST"])
@require_auth
async def add_reaction_rest():
    """Add reaction to message"""
    data = await request.get_json()
    channel_id = data.get("channel_id")
    message_id = data.get("message_id")
    emoji = data.get("emoji")

    if not all([channel_id, message_id, emoji]):
        return jsonify({"error": "Missing required fields"}), 400

    success, error = await discord_service.add_reaction(channel_id, message_id, emoji)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/role", methods=["POST"])
@require_auth
async def manage_role_rest():
    """Add or remove role from user"""
    data = await request.get_json()
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    role_id = data.get("role_id")
    action = data.get("action", "add")

    if not all([guild_id, user_id, role_id]):
        return jsonify({"error": "Missing required fields"}), 400

    success, error = await discord_service.manage_role(
        guild_id, user_id, role_id, action
    )

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/webhook", methods=["POST"])
@require_auth
async def create_webhook_rest():
    """Create webhook for channel"""
    data = await request.get_json()
    channel_id = data.get("channel_id")
    name = data.get("name", "WaddleBot")

    if not channel_id:
        return jsonify({"error": "Missing channel_id"}), 400

    success, webhook_url, error = await discord_service.create_webhook(
        channel_id, name
    )

    if success:
        return jsonify({"success": True, "webhook_url": webhook_url})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/webhook/send", methods=["POST"])
@require_auth
async def send_webhook_rest():
    """Send message via webhook"""
    data = await request.get_json()
    webhook_url = data.get("webhook_url")
    content = data.get("content")
    embeds = data.get("embeds")

    if not webhook_url or not content:
        return jsonify({"error": "Missing webhook_url or content"}), 400

    success, error = await discord_service.send_webhook(webhook_url, content, embeds)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/message/<channel_id>/<message_id>", methods=["DELETE"])
@require_auth
async def delete_message_rest(channel_id: str, message_id: str):
    """Delete message"""
    success, error = await discord_service.delete_message(channel_id, message_id)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/message/<channel_id>/<message_id>", methods=["PATCH"])
@require_auth
async def edit_message_rest(channel_id: str, message_id: str):
    """Edit message"""
    data = await request.get_json()
    content = data.get("content")

    if not content:
        return jsonify({"error": "Missing content"}), 400

    success, error = await discord_service.edit_message(channel_id, message_id, content)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/moderation/kick", methods=["POST"])
@require_auth
async def kick_user_rest():
    """Kick user from guild"""
    data = await request.get_json()
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    reason = data.get("reason")

    if not all([guild_id, user_id]):
        return jsonify({"error": "Missing required fields"}), 400

    success, error = await discord_service.kick_user(guild_id, user_id, reason)

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/moderation/ban", methods=["POST"])
@require_auth
async def ban_user_rest():
    """Ban user from guild"""
    data = await request.get_json()
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    reason = data.get("reason")
    delete_message_days = data.get("delete_message_days", 0)

    if not all([guild_id, user_id]):
        return jsonify({"error": "Missing required fields"}), 400

    success, error = await discord_service.ban_user(
        guild_id, user_id, reason, delete_message_days
    )

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


@app.route("/api/v1/moderation/timeout", methods=["POST"])
@require_auth
async def timeout_user_rest():
    """Timeout user for specified duration"""
    data = await request.get_json()
    guild_id = data.get("guild_id")
    user_id = data.get("user_id")
    duration_seconds = data.get("duration_seconds")
    reason = data.get("reason")

    if not all([guild_id, user_id, duration_seconds]):
        return jsonify({"error": "Missing required fields"}), 400

    success, error = await discord_service.timeout_user(
        guild_id, user_id, duration_seconds, reason
    )

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": error}), 500


# gRPC Server


async def serve_grpc():
    """Start gRPC server"""
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[AuthInterceptor()],
    )
    discord_action_pb2_grpc.add_DiscordActionServicer_to_server(
        DiscordActionServicer(discord_service), server
    )
    server.add_insecure_port(f"{Config.HOST}:{Config.GRPC_PORT}")
    logger.info(f"Starting gRPC server on {Config.HOST}:{Config.GRPC_PORT}")
    await server.start()
    await server.wait_for_termination()


async def serve_rest():
    """Start REST API server"""
    config = HypercornConfig()
    config.bind = [f"{Config.HOST}:{Config.REST_PORT}"]
    config.workers = 4
    logger.info(f"Starting REST API server on {Config.HOST}:{Config.REST_PORT}")
    await serve(app, config)


async def main():
    """Main entry point"""
    # Validate configuration
    errors, warnings = Config.validate()
    if errors:
        logger.error(f"Configuration errors: {errors}")
        sys.exit(1)

    if warnings:
        for warning in warnings:
            logger.warning(warning)

    logger.info(f"Starting {Config.MODULE_NAME} v{Config.MODULE_VERSION}")
    logger.info(f"Configuration: {Config.get_summary()}")

    # TODO: Implement periodic polling from hub module for credential updates
    # This will allow dynamic credential provisioning without service restart

    try:
        # Run both gRPC and REST servers
        await asyncio.gather(serve_grpc(), serve_rest())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await discord_service.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
