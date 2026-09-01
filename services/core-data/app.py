"""
Core Data Service - Combined Quart Application

Merges 4 core modules into a single service on port 8040:
1. Analytics Core Module (/api/v1/analytics)
2. Engagement Module (/api/v1)
3. Reputation Module (/api/v1, /api/v1/admin)
4. Labels Core Module (/api/v1)
"""
import os
import sys
import asyncio

# Ensure libs are accessible
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'libs'))

from quart import Quart, Blueprint, request

# Import core utilities
from flask_core import (
    setup_aaa_logging,
    init_database,
    success_response,
    error_response,
    create_health_blueprint,
)

# Create Quart app
app = Quart(__name__)

# ============================================================================
# Configuration & Setup
# ============================================================================

from config import Config

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, "0.0.1")
app.register_blueprint(health_bp)

# Logger setup
logger = setup_aaa_logging(Config.MODULE_NAME, "0.0.1")

# Global service instances
dal = None

# Analytics services
analytics_service = None
metrics_service = None
polling_service = None
bot_score_service = None
user_stats_service = None
platform_stats_service = None

# Reputation services
weight_manager = None
reputation_service = None
event_processor = None
policy_enforcer = None
grpc_server = None


# ============================================================================
# Service Key Validation Middleware
# ============================================================================

@app.before_request
async def validate_service_key():
    """
    Validate X-Service-Key header on all non-health endpoints.
    Health check (/healthz) is exempt so orchestrators can probe liveness.
    """
    if request.path.startswith('/health') or request.path == '/':
        return None
    service_key = request.headers.get('X-Service-Key', '')
    if not service_key or service_key != Config.SERVICE_API_KEY:
        logger.warning(
            "Unauthorized request: missing or invalid X-Service-Key",
            path=request.path,
            method=request.method,
        )
        return error_response("Unauthorized: invalid service key", 401)
    return None


# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.before_serving
async def startup():
    """Initialize services on startup."""
    global dal, analytics_service, metrics_service, polling_service
    global bot_score_service, user_stats_service, platform_stats_service
    global weight_manager, reputation_service, event_processor, policy_enforcer, grpc_server

    logger.system("Starting core-data service", action="startup")

    try:
        # Initialize shared database
        dal = init_database(Config.DATABASE_URL)
        app.config['dal'] = dal
        logger.system("Database initialized", result="SUCCESS")

        # ====================================================================
        # Analytics Module Initialization
        # ====================================================================
        try:
            from core.analytics_core_module.services.analytics_service import AnalyticsService
            from core.analytics_core_module.services.metrics_service import MetricsService
            from core.analytics_core_module.services.polling_service import PollingService
            from core.analytics_core_module.services.bot_score_service import BotScoreService
            from core.analytics_core_module.services.user_stats_service import UserStatsService
            from core.analytics_core_module.services.platform_stats_service import PlatformStatsService

            analytics_service = AnalyticsService(dal, logger)
            metrics_service = MetricsService(dal, logger)
            polling_service = PollingService(dal, logger)
            bot_score_service = BotScoreService(dal, logger)
            user_stats_service = UserStatsService(dal, logger)
            platform_stats_service = PlatformStatsService(dal, logger)

            from core.analytics_core_module.blueprints.user_bp import init_user_blueprint
            from core.analytics_core_module.blueprints.platform_bp import init_platform_blueprint
            init_user_blueprint(user_stats_service)
            init_platform_blueprint(platform_stats_service)

            logger.system("Analytics services initialized", result="SUCCESS")
        except Exception as e:
            logger.warning(f"Analytics services init skipped: {e}")

        # ====================================================================
        # Engagement Module Initialization
        # ====================================================================
        try:
            from core.engagement_module.app import init_database as engagement_init_db
            engagement_init_db()
            logger.system("Engagement module initialized", result="SUCCESS")
        except Exception as e:
            logger.warning(f"Engagement module init skipped: {e}")

        # ====================================================================
        # Reputation Module Initialization
        # ====================================================================
        try:
            from core.reputation_module.services.weight_manager import WeightManager
            from core.reputation_module.services.reputation_service import ReputationService
            from core.reputation_module.services.event_processor import EventProcessor
            from core.reputation_module.services.policy_enforcer import PolicyEnforcer
            from core.reputation_module.services.grpc_handler import ReputationServiceServicer
            from core.reputation_module.proto import reputation_pb2_grpc
            import grpc

            weight_manager = WeightManager(dal, logger)
            reputation_service = ReputationService(dal, weight_manager, logger)
            event_processor = EventProcessor(
                reputation_service, weight_manager, None, logger
            )
            policy_enforcer = PolicyEnforcer(weight_manager, dal, logger)
            event_processor.policy_enforcer = policy_enforcer

            # Initialize gRPC server for reputation
            grpc_server = grpc.aio.server()
            servicer = ReputationServiceServicer(reputation_service, event_processor)
            reputation_pb2_grpc.add_ReputationServiceServicer_to_server(servicer, grpc_server)

            grpc_server_address = f"0.0.0.0:{Config.GRPC_PORT}"
            grpc_server.add_insecure_port(grpc_server_address)
            await grpc_server.start()

            logger.system(
                "gRPC server started",
                action="grpc_startup",
                port=Config.GRPC_PORT,
                address=grpc_server_address
            )
            logger.system("Reputation services initialized", result="SUCCESS")
        except Exception as e:
            logger.warning(f"Reputation services init skipped: {e}")

        # ====================================================================
        # Labels Module Initialization
        # ====================================================================
        try:
            from core.labels_core_module.app import define_tables
            define_tables(dal)
            logger.system("Labels module initialized", result="SUCCESS")
        except Exception as e:
            logger.warning(f"Labels module init skipped: {e}")

        logger.system("core-data service started", result="SUCCESS")

    except Exception as e:
        logger.error(f"Startup failed: {e}", action="startup", result="FAILED")
        raise


@app.after_serving
async def shutdown():
    """Cleanup on shutdown."""
    global grpc_server, policy_enforcer

    logger.system("Shutting down core-data service", action="shutdown")

    # Shutdown gRPC server if running
    if grpc_server:
        try:
            await grpc_server.stop(grace=5)
            logger.system("gRPC server stopped", action="grpc_shutdown")
        except Exception as e:
            logger.warning(f"gRPC shutdown error: {e}")

    # Cleanup policy enforcer
    if policy_enforcer:
        try:
            await policy_enforcer.close()
        except Exception as e:
            logger.warning(f"Policy enforcer cleanup error: {e}")

    logger.system("core-data service shutdown complete", result="SUCCESS")


# ============================================================================
# Health & Status Endpoint (unified)
# ============================================================================

@app.route('/api/v1/status', methods=['GET'])
async def status():
    """Get unified status across all modules."""
    return success_response({
        'service': 'core-data',
        'version': '0.0.1',
        'status': 'healthy',
        'modules': [
            'analytics',
            'engagement',
            'reputation',
            'labels'
        ]
    })


# ============================================================================
# Register Blueprints from All Modules
# ============================================================================

def register_blueprints():
    """Register all blueprints from the 4 modules."""

    # ====================================================================
    # Analytics Module Blueprints
    # ====================================================================
    try:
        from core.analytics_core_module.app import (
            api_bp as analytics_api_bp,
            internal_bp as analytics_internal_bp,
            user_bp as analytics_user_bp,
            platform_bp as analytics_platform_bp,
        )
        app.register_blueprint(analytics_api_bp)
        app.register_blueprint(analytics_internal_bp)
        app.register_blueprint(analytics_user_bp)
        app.register_blueprint(analytics_platform_bp)
        logger.system("Analytics blueprints registered", result="SUCCESS")
    except Exception as e:
        logger.warning(f"Analytics blueprints registration skipped: {e}")

    # ====================================================================
    # Engagement Module Blueprints
    # ====================================================================
    try:
        from engagement_bp import engagement_bp
        app.register_blueprint(engagement_bp)
        logger.system("Engagement blueprints registered", result="SUCCESS")
    except Exception as e:
        logger.warning(f"Engagement blueprints registration skipped: {e}")

    # ====================================================================
    # Reputation Module Blueprints
    # ====================================================================
    try:
        from core.reputation_module.app import (
            api_bp as reputation_api_bp,
            internal_bp as reputation_internal_bp,
            admin_bp as reputation_admin_bp,
        )
        app.register_blueprint(reputation_api_bp)
        app.register_blueprint(reputation_internal_bp)
        app.register_blueprint(reputation_admin_bp)
        logger.system("Reputation blueprints registered", result="SUCCESS")
    except Exception as e:
        logger.warning(f"Reputation blueprints registration skipped: {e}")

    # ====================================================================
    # Labels Module Blueprints
    # ====================================================================
    try:
        from core.labels_core_module.app import api_bp as labels_api_bp
        app.register_blueprint(labels_api_bp)
        logger.system("Labels blueprints registered", result="SUCCESS")
    except Exception as e:
        logger.warning(f"Labels blueprints registration skipped: {e}")


# Register blueprints when module loads
register_blueprints()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    config.workers = 4

    logger.system(f"Starting core-data on port {Config.MODULE_PORT}")
    asyncio.run(hypercorn.asyncio.serve(app, config))
