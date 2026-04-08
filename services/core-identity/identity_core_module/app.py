"""Identity linking system - Quart Application"""
import asyncio
import os
import sys

from quart import Blueprint, Quart

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs'))

from config import Config  # noqa: E402
from flask_core import (  # noqa: E402
    async_endpoint, create_health_blueprint, init_database, setup_aaa_logging, success_response,
)
from services.grpc_handler import IdentityServiceServicer  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
grpc_server = None


@app.before_serving
async def startup():
    global dal, grpc_server
    logger.system("Starting identity_core_module", action="startup")
    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal

    # Start gRPC server
    try:
        import grpc
        from grpc import aio

        servicer = IdentityServiceServicer(dal=dal, logger=logger)
        grpc_server = aio.server()

        # Add IdentityService servicer to gRPC server
        # Note: Requires generated grpc service from proto files
        # For now, we create a simple gRPC server without reflection
        logger.system(f"gRPC server initialized (will listen on 0.0.0.0:{Config.GRPC_PORT})")

        # Start gRPC server in background
        asyncio.create_task(_start_grpc_server(grpc_server, logger))
    except Exception as e:
        logger.warning(f"Failed to initialize gRPC server: {str(e)}")
        logger.warning("Continuing with REST API only")

    logger.system("identity_core_module started", result="SUCCESS")


async def _start_grpc_server(server, logger):
    """Start the gRPC server"""
    try:
        server.add_insecure_port(f"0.0.0.0:{Config.GRPC_PORT}")
        await server.start()
        logger.system(f"gRPC server started on 0.0.0.0:{Config.GRPC_PORT}", action="grpc_startup")
        await server.wait_for_termination()
    except Exception as e:
        logger.error(f"gRPC server error: {str(e)}")


@app.after_serving
async def shutdown():
    global grpc_server
    if grpc_server:
        logger.system("Stopping gRPC server", action="grpc_shutdown")
        await grpc_server.stop(0)


@api_bp.route('/status')
@async_endpoint
async def status():
    return success_response({"status": "operational", "module": Config.MODULE_NAME})

app.register_blueprint(api_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
