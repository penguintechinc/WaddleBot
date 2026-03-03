"""
Google Chat Action Module - Main Application
Quart application with gRPC server for receiving tasks from processor
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
from services.googlechat_service import GoogleChatService
from services.grpc_handler import create_grpc_server


# Configure logging
logging.basicConfig(
    level=getattr(logging, Config.LOG_LEVEL),
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'{Config.LOG_DIR}/googlechat_action.log') if Config.LOG_DIR else logging.NullHandler()
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

# Initialize Google Chat service
googlechat_service = GoogleChatService(
    service_account_key_json=Config.GOOGLE_CHAT_SERVICE_ACCOUNT_KEY,
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

        result = await googlechat_service.send_message(
            community_id=data.get('community_id'),
            space_id=data.get('space_id'),
            text=data.get('text'),
            cards=data.get('cards'),
            thread_id=data.get('thread_id')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Send message API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/message/<string:message_id>', methods=['PUT'])
@require_auth
async def update_message_api(message_id: str):
    """REST API endpoint for updating messages"""
    try:
        data = await request.get_json()

        result = await googlechat_service.update_message(
            community_id=data.get('community_id'),
            message_id=message_id,
            text=data.get('text'),
            cards=data.get('cards')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Update message API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/message/<string:message_id>', methods=['DELETE'])
@require_auth
async def delete_message_api(message_id: str):
    """REST API endpoint for deleting messages"""
    try:
        data = await request.get_json()

        result = await googlechat_service.delete_message(
            community_id=data.get('community_id'),
            message_id=message_id
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Delete message API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/space', methods=['POST'])
@require_auth
async def create_space_api():
    """REST API endpoint for creating spaces"""
    try:
        data = await request.get_json()

        result = await googlechat_service.create_space(
            community_id=data.get('community_id'),
            display_name=data.get('display_name'),
            space_type=data.get('space_type', 'SPACE'),
            description=data.get('description')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Create space API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/card', methods=['POST'])
@require_auth
async def send_card_api():
    """REST API endpoint for sending cards (messages with cards)"""
    try:
        data = await request.get_json()

        result = await googlechat_service.send_message(
            community_id=data.get('community_id'),
            space_id=data.get('space_id'),
            text=data.get('text'),
            cards=data.get('cards'),
            thread_id=data.get('thread_id')
        )

        return jsonify(result), 200 if result['success'] else 500

    except Exception as e:
        logger.error(f"Send card API error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/v1/history/<string:community_id>', methods=['GET'])
@require_auth
async def get_action_history_api(community_id: str):
    """REST API endpoint for getting action history"""
    try:
        limit = request.args.get('limit', 100, type=int)

        history = await googlechat_service.get_action_history(
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

    logger.info("Starting Google Chat Action Module...")

    # Validate configuration
    errors = Config.validate()
    if errors:
        logger.error(f"Configuration errors: {', '.join(errors)}")
        sys.exit(1)

    logger.info(f"Configuration: {Config.get_info()}")

    # Start gRPC server
    grpc_server = create_grpc_server(
        googlechat_service=googlechat_service,
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

    logger.info("Shutting down Google Chat Action Module...")

    # Stop gRPC server
    if grpc_server:
        await grpc_server.stop(grace=5)
        logger.info("gRPC server stopped")

    # Close database connections
    db.close()
    logger.info("Database connections closed")


if __name__ == '__main__':
    # Run with Hypercorn in production
    # hypercorn app:app --bind 0.0.0.0:8074 --workers 4
    app.run(
        host='0.0.0.0',
        port=Config.REST_PORT,
        debug=False
    )
