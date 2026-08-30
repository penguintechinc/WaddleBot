"""Welcome Interaction Module (Quart).

social.welcome: recognize a user's first-ever message in a community and
welcome them -- via AI if the `waddles.social.welcome_ai` flag is on, else a
template. See services/welcome_service.py for the first-seen detection and
race-safe welcomed guard.
"""

import asyncio
import os
import sys
from typing import Any

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs'),
)

from flask_core import (  # noqa: E402
    async_endpoint,
    create_health_blueprint,
    error_response,
    init_database,
    setup_aaa_logging,
    success_response,
)
from flask_core.validation import validate_json  # noqa: E402
from quart import Blueprint, Quart  # noqa: E402
from services.ai_client_service import AIInteractionClient  # noqa: E402
from services.welcome_service import WelcomeService  # noqa: E402
from validation_models import WelcomeCheckRequest  # noqa: E402

from config import Config  # noqa: E402

app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')
logger = setup_aaa_logging(Config.MODULE_NAME, Config.MODULE_VERSION)

dal = None
welcome_service: WelcomeService | None = None


@app.before_serving
async def startup() -> None:
    """Initialize the DAL and welcome service on startup."""
    global dal, welcome_service
    logger.system("Starting welcome_interaction_module", action="startup")

    Config.validate()

    dal = init_database(Config.DATABASE_URL)
    app.config['dal'] = dal

    ai_client = AIInteractionClient(
        base_url=Config.AI_INTERACTION_URL,
        api_key=Config.AI_SERVICE_API_KEY,
        timeout_seconds=Config.AI_WELCOME_TIMEOUT_SECONDS,
    )
    welcome_service = WelcomeService(dal=dal, ai_client=ai_client)

    logger.system("welcome_interaction_module started", result="SUCCESS")


@api_bp.route('/status')
@async_endpoint
async def status() -> tuple[dict[str, Any], int]:
    """Return the module status."""
    return success_response({
        "status": "operational",
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
    })


# This is the process-stage HTTP endpoint the v2 router calls per incoming
# message today. The v3 form of this same check is a stream consumer on the
# process stage (flask_core.stream_pipeline) rather than a synchronous HTTP
# call -- this handler's body (WelcomeService.check_and_welcome) is what
# migrates, unchanged, when that stream consumer is wired up.
@api_bp.route('/welcome/check', methods=['POST'])
@validate_json(WelcomeCheckRequest)
@async_endpoint
async def welcome_check(
    validated_data: WelcomeCheckRequest,
) -> tuple[dict[str, Any], int]:
    """Check whether a message sender is first-time and welcome them if so.

    Atomically claims and sends the one-time welcome for a genuinely
    first-time community member; a no-op for anyone already seen.

    Request JSON:
    {
        "community_id": 123,
        "platform": "twitch",
        "platform_user_id": "456",
        "platform_username": "jdoe",
        "tenant": "global"
    }
    """
    if welcome_service is None:
        return error_response("Service not yet initialized", status_code=503)

    try:
        logger.audit(
            action="welcome_check",
            community=validated_data.community_id,
            target_user=validated_data.platform_user_id,
            result="STARTED",
        )

        result = await welcome_service.check_and_welcome(
            community_id=validated_data.community_id,
            platform=validated_data.platform,
            platform_user_id=validated_data.platform_user_id,
            platform_username=validated_data.sanitized_username(),
            tenant=validated_data.tenant,
        )

        logger.audit(
            action="welcome_check",
            community=validated_data.community_id,
            target_user=validated_data.platform_user_id,
            result="SUCCESS" if result.welcomed else "SKIPPED",
        )

        if not result.welcomed:
            return success_response({"welcomed": False})

        return success_response({
            "welcomed": True,
            "message": result.message,
            "source": result.source,
        })

    except Exception as e:
        logger.error(f"Failed to process welcome check: {e}")
        return error_response(str(e), status_code=500)


app.register_blueprint(api_bp)

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig
    config = HyperConfig()
    config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
