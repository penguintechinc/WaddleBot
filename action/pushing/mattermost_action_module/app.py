import asyncio
import logging
from contextlib import asynccontextmanager

import jwt
from quart import Quart, request, jsonify
from pydal import DAL, Field

from config import Config
from services.mattermost_service import MattermostService
from services.grpc_handler import create_grpc_server

logger = logging.getLogger(__name__)


class AppState:
    """Holds app state: db, service, grpc_server."""
    def __init__(self):
        self.db = None
        self.service = None
        self.grpc_server = None
        self.grpc_task = None


app_state = AppState()


def init_db():
    """Initialize PyDAL database connection."""
    db = DAL(Config.DATABASE_URL, migrate=True)

    # Define action history table
    db.define_table(
        'action_history',
        Field('action_type', 'string', requires=IS_NOT_EMPTY()),
        Field('channel_id', 'string'),
        Field('message_id', 'string'),
        Field('user_id', 'string'),
        Field('payload', 'json'),
        Field('response', 'json'),
        Field('status', 'string', default='success'),
        Field('error_message', 'string'),
        Field('created_at', 'datetime', default=lambda: __import__('datetime').datetime.utcnow()),
    )

    db.commit()
    return db


def verify_jwt(token):
    """Verify JWT token from Authorization header."""
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator to require JWT authentication."""
    async def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid authorization'}), 401

        token = auth_header[7:]  # Remove 'Bearer ' prefix
        payload = verify_jwt(token)

        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        return await f(*args, **kwargs)

    decorated.__name__ = f.__name__
    return decorated


@asynccontextmanager
async def lifespan(app: Quart):
    """Handle app startup and shutdown."""
    logger.info("Starting Mattermost Action Module")

    # Startup
    app_state.db = init_db()
    app_state.service = MattermostService(
        mattermost_url=Config.MATTERMOST_URL,
        bot_token=Config.MATTERMOST_BOT_TOKEN,
        db=app_state.db,
    )

    # Start gRPC server
    app_state.grpc_server, app_state.grpc_task = await create_grpc_server(
        grpc_port=Config.GRPC_PORT,
        service=app_state.service,
    )

    logger.info(f"gRPC server started on port {Config.GRPC_PORT}")
    logger.info(f"REST server listening on port {Config.REST_PORT}")

    yield

    # Shutdown
    logger.info("Shutting down Mattermost Action Module")
    if app_state.grpc_server:
        await app_state.grpc_server.stop(0)
    if app_state.grpc_task:
        app_state.grpc_task.cancel()
        try:
            await app_state.grpc_task
        except asyncio.CancelledError:
            pass

    if app_state.db:
        app_state.db.close()


app = Quart(__name__, )
app.lifespan_context = lifespan


@app.route('/health', methods=['GET'])
async def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'module': Config.MODULE_NAME,
        'version': Config.MODULE_VERSION,
    }), 200


@app.route('/api/v1/message', methods=['POST'])
@require_auth
async def send_message():
    """Send a message to a Mattermost channel."""
    try:
        data = await request.get_json()

        # Validate required fields
        channel_id = data.get('channel_id')
        message = data.get('message')

        if not channel_id or not message:
            return jsonify({'error': 'Missing channel_id or message'}), 400

        # Send message via service
        result = await app_state.service.send_message(
            channel_id=channel_id,
            message=message,
            attachments=data.get('attachments'),
            metadata=data.get('metadata'),
        )

        # Log action
        app_state.db.action_history.insert(
            action_type='send_message',
            channel_id=channel_id,
            payload=data,
            response=result,
            status='success' if result.get('success') else 'failed',
        )
        app_state.db.commit()

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.exception("Error sending message")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/v1/ephemeral', methods=['POST'])
@require_auth
async def send_ephemeral():
    """Send an ephemeral (temporary) message to a user in a channel."""
    try:
        data = await request.get_json()

        channel_id = data.get('channel_id')
        user_id = data.get('user_id')
        message = data.get('message')

        if not channel_id or not user_id or not message:
            return jsonify({'error': 'Missing channel_id, user_id, or message'}), 400

        result = await app_state.service.send_ephemeral(
            channel_id=channel_id,
            user_id=user_id,
            message=message,
            attachments=data.get('attachments'),
        )

        app_state.db.action_history.insert(
            action_type='send_ephemeral',
            channel_id=channel_id,
            user_id=user_id,
            payload=data,
            response=result,
            status='success' if result.get('success') else 'failed',
        )
        app_state.db.commit()

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.exception("Error sending ephemeral message")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/v1/reaction', methods=['POST'])
@require_auth
async def add_reaction():
    """Add a reaction/emoji to a message."""
    try:
        data = await request.get_json()

        message_id = data.get('message_id')
        emoji_name = data.get('emoji_name')
        action_type = data.get('action_type', 'add')  # 'add' or 'remove'

        if not message_id or not emoji_name:
            return jsonify({'error': 'Missing message_id or emoji_name'}), 400

        if action_type == 'remove':
            result = await app_state.service.remove_reaction(
                message_id=message_id,
                emoji_name=emoji_name,
            )
        else:
            result = await app_state.service.add_reaction(
                message_id=message_id,
                emoji_name=emoji_name,
            )

        app_state.db.action_history.insert(
            action_type=f'{action_type}_reaction',
            message_id=message_id,
            payload=data,
            response=result,
            status='success' if result.get('success') else 'failed',
        )
        app_state.db.commit()

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.exception("Error handling reaction")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/v1/channel', methods=['POST'])
@require_auth
async def create_channel():
    """Create a new Mattermost channel."""
    try:
        data = await request.get_json()

        channel_name = data.get('channel_name')
        display_name = data.get('display_name')

        if not channel_name:
            return jsonify({'error': 'Missing channel_name'}), 400

        result = await app_state.service.create_channel(
            channel_name=channel_name,
            display_name=display_name or channel_name,
            is_private=data.get('is_private', False),
            purpose=data.get('purpose'),
        )

        app_state.db.action_history.insert(
            action_type='create_channel',
            channel_id=result.get('channel_id'),
            payload=data,
            response=result,
            status='success' if result.get('success') else 'failed',
        )
        app_state.db.commit()

        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.exception("Error creating channel")
        return jsonify({'error': str(e), 'success': False}), 500


@app.route('/api/v1/token', methods=['GET'])
async def get_token():
    """Health/info endpoint for token validation (no auth required for health check)."""
    return jsonify({
        'status': 'healthy',
        'module': Config.MODULE_NAME,
        'version': Config.MODULE_VERSION,
        'requires_auth': True,
    }), 200


if __name__ == '__main__':
    import hypercorn.asyncio

    config = hypercorn.asyncio.Config()
    config.bind = [f'0.0.0.0:{Config.REST_PORT}']

    asyncio.run(hypercorn.asyncio.serve(app, config))
