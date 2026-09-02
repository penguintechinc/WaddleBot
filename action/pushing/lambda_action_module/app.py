"""
Lambda Action Module - Main Application

Stateless, clusterable module for pushing actions to AWS Lambda
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
from grpc_proto import lambda_action_pb2_grpc
from pydal import DAL
from quart import Quart, jsonify, request

from config import Config
from services.lambda_service import LambdaService
from services.grpc_auth_interceptor import AuthInterceptor
from services.grpc_handler import LambdaActionServicer
from services.grpc_tls import bind_secure_port, default_server_options

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

# Initialize Lambda service
lambda_service = LambdaService(db)


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


@app.route("/api/v1/invoke", methods=["POST"])
@require_auth
async def invoke_function_rest():
    """
    Invoke Lambda function

    Request body:
    {
        "function_name": "string",
        "payload": "string",
        "invocation_type": "RequestResponse|Event|DryRun",
        "alias": "string",  // optional
        "version": "string"  // optional
    }
    """
    data = await request.get_json()
    function_name = data.get("function_name")
    payload = data.get("payload")
    invocation_type = data.get("invocation_type", "RequestResponse")
    alias = data.get("alias")
    version = data.get("version")

    if not function_name or not payload:
        return jsonify({"error": "Missing function_name or payload"}), 400

    success, status_code, response_payload, func_error, log_result, exec_version = \
        await lambda_service.invoke_function(
            function_name, payload, invocation_type, alias, version
        )

    if success:
        return jsonify({
            "success": True,
            "status_code": status_code,
            "payload": response_payload,
            "executed_version": exec_version,
            "log_result": log_result
        })
    else:
        return jsonify({
            "success": False,
            "error": func_error or exec_version,  # exec_version contains error on failure
            "status_code": status_code
        }), 500


@app.route("/api/v1/invoke-async", methods=["POST"])
@require_auth
async def invoke_async_rest():
    """
    Invoke Lambda function asynchronously

    Request body:
    {
        "function_name": "string",
        "payload": "string"
    }
    """
    data = await request.get_json()
    function_name = data.get("function_name")
    payload = data.get("payload")

    if not function_name or not payload:
        return jsonify({"error": "Missing function_name or payload"}), 400

    success, status_code, request_id = await lambda_service.invoke_async(
        function_name, payload
    )

    if success:
        return jsonify({
            "success": True,
            "status_code": status_code,
            "request_id": request_id
        })
    else:
        return jsonify({
            "success": False,
            "error": request_id,  # request_id contains error on failure
            "status_code": status_code
        }), 500


@app.route("/api/v1/batch", methods=["POST"])
@require_auth
async def batch_invoke_rest():
    """
    Batch invoke Lambda functions

    Request body:
    {
        "invocations": [
            {
                "function_name": "string",
                "payload": "string",
                "invocation_type": "RequestResponse",
                "alias": "string",
                "version": "string"
            }
        ]
    }
    """
    data = await request.get_json()
    invocations = data.get("invocations", [])

    if not invocations:
        return jsonify({"error": "Missing invocations list"}), 400

    results = []

    for invocation in invocations:
        function_name = invocation.get("function_name")
        payload = invocation.get("payload")
        invocation_type = invocation.get("invocation_type", "RequestResponse")
        alias = invocation.get("alias")
        version = invocation.get("version")

        if not function_name or not payload:
            results.append({
                "success": False,
                "error": "Missing function_name or payload"
            })
            continue

        success, status_code, response_payload, func_error, log_result, exec_version = \
            await lambda_service.invoke_function(
                function_name, payload, invocation_type, alias, version
            )

        results.append({
            "success": success,
            "status_code": status_code,
            "payload": response_payload if success else None,
            "error": func_error if not success else None,
            "executed_version": exec_version,
            "log_result": log_result
        })

    return jsonify({"results": results})


@app.route("/api/v1/functions", methods=["GET"])
@require_auth
async def list_functions_rest():
    """
    List Lambda functions

    Query parameters:
    - max_items: Maximum number of functions to return (default: 50)
    - next_marker: Pagination marker
    """
    max_items = request.args.get("max_items", 50, type=int)
    next_marker = request.args.get("next_marker")

    success, functions, next_marker = await lambda_service.list_functions(
        max_items, next_marker
    )

    if success:
        return jsonify({
            "success": True,
            "functions": functions,
            "next_marker": next_marker
        })
    else:
        return jsonify({
            "success": False,
            "error": next_marker  # next_marker contains error on failure
        }), 500


@app.route("/api/v1/functions/<function_name>", methods=["GET"])
@require_auth
async def get_function_config_rest(function_name: str):
    """Get Lambda function configuration"""
    success, config = await lambda_service.get_function_config(function_name)

    if success:
        return jsonify({
            "success": True,
            "config": config
        })
    else:
        return jsonify({
            "success": False,
            "error": "Failed to retrieve function configuration"
        }), 500


# gRPC Server


async def serve_grpc():
    """Start gRPC server"""
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        interceptors=[AuthInterceptor()],
        options=default_server_options(),
    )
    lambda_action_pb2_grpc.add_LambdaActionServicer_to_server(
        LambdaActionServicer(lambda_service), server
    )
    bind_secure_port(server, f"{Config.HOST}:{Config.GRPC_PORT}")
    logger.info(f"Starting gRPC server (TLS) on {Config.HOST}:{Config.GRPC_PORT}")
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
    errors = Config.validate()
    if errors:
        logger.error(f"Configuration errors: {errors}")
        sys.exit(1)

    logger.info(f"Starting {Config.MODULE_NAME} v{Config.MODULE_VERSION}")
    logger.info(f"Configuration: {Config.get_summary()}")

    try:
        # Run both gRPC and REST servers
        await asyncio.gather(serve_grpc(), serve_rest())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await lambda_service.close()
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
