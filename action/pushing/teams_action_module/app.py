"""
Teams Action Module - Main Application
Flask/Quart application with gRPC server for receiving tasks from processor
and REST API for third-party use
"""
import asyncio
import logging
import sys
from typing import Optional

from quart import Quart, request, jsonify
from pydal import DAL
import jwt
from functools import wraps

from config import Config
from services.teams_service import TeamsService
from services.grpc_handler import create_grpc_server


# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'{Config.LOG_DIR}/teams_action.log') if Config.LOG_DIR else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize Quart app
app = Quart(__name__)
app.config.from_object(Config)

# Initialize database
# Use fake_migrate=True to check schema without trying to create tables
db = DAL(
    Config.DATABASE_URL,
    folder='/tmp/pydal',
    pool_size=10,
    migrate_enabled=False,
    fake_migrate_all=True
)

# Initialize Teams service
teams_service = TeamsService(
    app_id=Config.TEAMS_APP_ID,
    app_password=Config.TEAMS_APP_PASSWORD,
    db=db
)

# gRPC server instance
grpc_server = None


def require_auth(f):
    """JWT authentication decorator for REST API"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({'error': 'No authorization header'}), 401

        try:
            # Extract token from "Bearer <token>"
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'Invalid authorization scheme'}), 401

            # Verify JWT
            payload = jwt.decode(
                token,
                Config.MODULE_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )

            # Add payload to request context
            request.jwt_payload = payload

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except ValueError:
            return jsonify({'error': 'Invalid authorization header format'}), 401

        return await f(*args, **kwargs)

    return decorated_function


# ============================================================================
# REST API Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connectivity
        db.executesql('SELECT 1')

        return jsonify({
            'status': 'healthy',
            'module': Config.MODULE_NAME,
            'version': Config.MODULE_VERSION,
            'grpc_port': Config.GRPC_PORT,
            'rest_port': Config.REST_PORT
        }), 200

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/api/v1/message', methods=['POST'])
@require_auth
async def send_message_api():
    """REST API endpoint for sending messages"""
    try:
        data = await request.get_json()

        result = await teams_service.send_message(
            community_id=data.get('community_id'),
            channel_id=data.get('channel_id'),
            text=data.get('text'),
            blocks=data.get('blocks'),
            thread_ts=data.get('thread_ts')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Send message API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/ephemeral', methods=['POST'])
@require_auth
async def send_ephemeral_api():
    """REST API endpoint for sending ephemeral messages"""
    try:
        data = await request.get_json()

        result = await teams_service.send_ephemeral(
            community_id=data.get('community_id'),
            channel_id=data.get('channel_id'),
            user_id=data.get('user_id'),
            text=data.get('text')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Send ephemeral API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/message/<string:channel_id>/<string:ts>', methods=['PUT'])
@require_auth
async def update_message_api(channel_id: str, ts: str):
    """REST API endpoint for updating messages"""
    try:
        data = await request.get_json()

        result = await teams_service.update_message(
            community_id=data.get('community_id'),
            channel_id=channel_id,
            ts=ts,
            text=data.get('text'),
            blocks=data.get('blocks')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Update message API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/message/<string:channel_id>/<string:ts>', methods=['DELETE'])
@require_auth
async def delete_message_api(channel_id: str, ts: str):
    """REST API endpoint for deleting messages"""
    try:
        data = await request.get_json()

        result = await teams_service.delete_message(
            community_id=data.get('community_id'),
            channel_id=channel_id,
            ts=ts
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Delete message API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/modal', methods=['POST'])
@require_auth
async def open_modal_api():
    """REST API endpoint for opening modals"""
    try:
        data = await request.get_json()

        result = await teams_service.open_modal(
            community_id=data.get('community_id'),
            trigger_id=data.get('trigger_id'),
            view=data.get('view')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Open modal API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/history/<string:community_id>', methods=['GET'])
@require_auth
async def get_action_history_api(community_id: str):
    """REST API endpoint for getting action history"""
    try:
        limit = request.args.get('limit', 100, type=int)

        history = await teams_service.get_action_history(
            community_id=community_id,
            limit=limit
        )

        return jsonify({'history': history}), 200

    except Exception as e:
        logger.error(f"Get history API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/token', methods=['POST'])
async def generate_token():
    """Generate JWT token for API authentication"""
    try:
        data = await request.get_json()

        # In production, verify credentials against database
        api_key = data.get('api_key')
        if api_key != Config.MODULE_SECRET_KEY:
            return jsonify({'error': 'Invalid API key'}), 401

        # Generate JWT token
        import time
        payload = {
            'exp': int(time.time()) + Config.JWT_EXPIRY_SECONDS,
            'iat': int(time.time()),
            'sub': data.get('client_id', 'default')
        }

        token = jwt.encode(
            payload,
            Config.MODULE_SECRET_KEY,
            algorithm=Config.JWT_ALGORITHM
        )

        return jsonify({
            'token': token,
            'expires_in': Config.JWT_EXPIRY_SECONDS
        }), 200

    except Exception as e:
        logger.error(f"Token generation error: {e}")
        return jsonify({'error': str(e)}), 500


# ============================================================================
# Application Lifecycle
# ============================================================================

@app.before_serving
async def startup():
    """Application startup"""
    global grpc_server

    logger.info("Starting Teams Action Module...")

    # Validate configuration
    errors = Config.validate()
    if errors:
        logger.error(f"Configuration errors: {', '.join(errors)}")
        sys.exit(1)

    logger.info(f"Configuration: {Config.get_info()}")

    # Start gRPC server
    grpc_server = create_grpc_server(
        teams_service=teams_service,
        port=Config.GRPC_PORT,
        max_workers=Config.GRPC_MAX_WORKERS
    )

    if grpc_server:
        await grpc_server.start()
        logger.info(f"gRPC server started on port {Config.GRPC_PORT}")
    else:
        logger.warning("gRPC server not started - proto files may not be generated")

    logger.info(f"REST API started on port {Config.REST_PORT}")


@app.after_serving
async def shutdown():
    """Application shutdown"""
    global grpc_server

    logger.info("Shutting down Teams Action Module...")

    # Stop gRPC server
    if grpc_server:
        await grpc_server.stop(grace=5)
        logger.info("gRPC server stopped")

    # Close database connections
    db.close()
    logger.info("Database connections closed")


if __name__ == '__main__':
    # Run with Hypercorn in production
    # hypercorn app:app --bind 0.0.0.0:8072 --workers 4
    app.run(
        host='0.0.0.0',
        port=Config.REST_PORT,
        debug=False
    )
