"""
WaddleBot AI Interaction Module (Quart)
========================================

AI-powered chat interactions with multiple provider support:
- Ollama: Direct connection with configurable host:port and TLS
- WaddleAI: Centralized proxy for OpenAI, Claude, MCP, and other providers

Converted from py4web to Quart for better async performance.
"""

import os
import sys
import asyncio  # noqa: E402
from datetime import datetime  # noqa: E402

# Add libs to path for flask_core imports
sys.path.insert(  # noqa: E402
    0,
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'libs')
)

from quart import Quart, Blueprint, request  # noqa: E402

from flask_core import (  # noqa: E402
    setup_aaa_logging,
    async_endpoint,
    auth_required,
    success_response,
    error_response,
    create_health_blueprint,
    validate_json
)
from flask_core.sanitization import sanitize_input  # noqa: E402

from config import Config  # noqa: E402
from services.ai_service import AIService  # noqa: E402
from services.router_service import RouterService  # noqa: E402
from validation_models import (  # noqa: E402
    InteractionRequest,
    ProviderConfigRequest
)

# Initialize Quart app
app = Quart(__name__)

# Register health/metrics endpoints
health_bp = create_health_blueprint(Config.MODULE_NAME, Config.MODULE_VERSION)
app.register_blueprint(health_bp)

ai_bp = Blueprint('ai', __name__, url_prefix='/api/v1/ai')

# Setup logging
logger = setup_aaa_logging(
    module_name=Config.MODULE_NAME,
    version=Config.MODULE_VERSION,
    log_level=Config.LOG_LEVEL
)

# Initialize services
ai_service = None
router_service = None
chatter_config_service = None
chatter_rate_limiter = None
proactive_chat_service = None


@app.before_serving
async def startup():
    """Initialize services on startup"""
    global ai_service, router_service, chatter_config_service, chatter_rate_limiter, proactive_chat_service

    logger.system("Starting AI interaction module", action="startup")

    try:
        # Initialize AI service
        ai_service = AIService.create()
        logger.system(  # noqa: E501
            f"Initialized AI service with provider: {Config.AI_PROVIDER}"
        )

        # Initialize router service
        router_service = RouterService()
        logger.system("Initialized router service")

        # Health check
        is_healthy = await ai_service.health_check()
        if is_healthy:
            logger.system("AI provider health check passed", result="SUCCESS")
        else:
            logger.error("AI provider health check failed", result="FAILED")

        # Initialize AIChatter services
        from services.chatter_config_service import ChatterConfigService
        from services.chatter_rate_limiter import ChatterRateLimiter
        from services.proactive_chat_service import ProactiveChatService

        # Get Redis client if available
        redis_client = None
        try:
            import redis.asyncio as aioredis
            redis_url = os.getenv('REDIS_URL', '')
            if redis_url:
                redis_client = aioredis.from_url(redis_url)
        except Exception as redis_err:
            logger.warning(f"Redis not available for chatter: {redis_err}")

        chatter_config_service = ChatterConfigService(None, redis_client, logger)
        chatter_rate_limiter = ChatterRateLimiter(redis_client, None)
        proactive_chat_service = ProactiveChatService(
            ai_service, chatter_config_service, chatter_rate_limiter, logger
        )
        logger.system("Initialized AIChatter services")

    except Exception as e:
        logger.error(f"Startup failed: {e}", action="startup", result="ERROR")
        raise


@app.after_serving
async def shutdown():
    """Cleanup on shutdown"""
    logger.system("Shutting down AI interaction module", action="shutdown")


# Module info endpoint at root (direct access)
@app.route('/', methods=['GET'])
@app.route('/index', methods=['GET'])
async def index():
    """Module information and status"""
    return success_response({
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
        "provider": Config.AI_PROVIDER,
        "model": Config.AI_MODEL,
        "status": "operational",
        "endpoints": [
            "/health",
            "/api/v1/ai/status",
            "/api/v1/ai/interaction",
            "/api/v1/ai/chat/completions",
            "/api/v1/ai/models",
            "/api/v1/ai/config",
            "/api/v1/ai/test"
        ]
    })


# Status endpoint (follows standard module pattern for Kong routing)
@ai_bp.route('/status', methods=['GET'])
@async_endpoint
async def status():
    """Module status endpoint - follows standard pattern for Kong routing"""
    provider_healthy = False
    if ai_service:
        try:
            provider_healthy = await ai_service.health_check()
        except Exception:
            pass

    return success_response({
        "module": Config.MODULE_NAME,
        "version": Config.MODULE_VERSION,
        "status": "operational" if provider_healthy else "degraded",
        "provider": Config.AI_PROVIDER,
        "model": Config.AI_MODEL,
        "provider_healthy": provider_healthy
    })


# Main interaction endpoint
@ai_bp.route('/interaction', methods=['POST'])
@validate_json(InteractionRequest)
@async_endpoint
async def interaction(validated_data: InteractionRequest):
    """
    Main interaction endpoint for processing messages and events.

    Expected JSON:
    {
        "session_id": "sess_123",
        "message_type": "chatMessage",
        "message_content": "Hello!",
        "user_id": "user123",
        "entity_id": "twitch:channel:456",
        "platform": "twitch",
        "username": "john_doe",
        "display_name": "John Doe"
    }
    """
    try:
        # Extract validated fields
        session_id = validated_data.session_id
        message_type = validated_data.message_type
        message_content = validated_data.message_content
        user_id = validated_data.user_id
        entity_id = validated_data.entity_id
        platform = validated_data.platform
        username = validated_data.username

        logger.audit(
            action="process_interaction",
            user=username,
            community=entity_id,
            result="STARTED",
            message_type=message_type
        )

        # Process interaction asynchronously (don't wait for result)
        asyncio.create_task(
            process_interaction(
                session_id, message_type, message_content,
                user_id, entity_id, platform, username,
                validated_data.dict()
            )
        )

        # Return immediate response
        return success_response({
            "message": "Processing request",
            "session_id": session_id
        })

    except Exception as e:
        logger.error(f"Interaction endpoint error: {e}")
        return error_response(str(e), status_code=500)


async def process_interaction(
    session_id: str,
    message_type: str,
    message_content: str,
    user_id: str,
    entity_id: str,
    platform: str,
    username: str,
    full_data: dict
):
    """Process interaction asynchronously"""
    start_time = datetime.utcnow()

    try:
        # Determine if we should respond
        should_respond = False
        response_context = {}

        if message_type == 'chatMessage':
            # Check for greeting patterns
            greeting_patterns = [  # noqa: E501
                'o7', 'hi', 'hello', 'hey', 'howdy', 'greetings', 'sup', 'hiya'
            ]
            farewell_patterns = [  # noqa: E501
                '!lurk', 'bye', 'goodbye', 'later', 'cya'
            ]

            message_lower = message_content.lower().strip()

            # Check greetings
            for pattern in greeting_patterns:
                if pattern in message_lower:
                    should_respond = True
                    response_context['trigger_type'] = 'greeting'
                    response_context['trigger'] = pattern
                    break

            # Check farewells
            if not should_respond:
                for pattern in farewell_patterns:
                    if pattern in message_lower:
                        should_respond = True
                        response_context['trigger_type'] = 'farewell'
                        response_context['trigger'] = pattern
                        break

            # Check question triggers
            if not should_respond:
                for trigger in Config.QUESTION_TRIGGERS:
                    if trigger in message_content:
                        should_respond = True
                        response_context['trigger_type'] = 'question'
                        response_context['trigger'] = trigger
                        break

        elif (message_type in Config.EVENT_RESPONSE_TYPES and  # noqa: E501
              Config.RESPOND_TO_EVENTS):
            should_respond = True
            response_context['trigger_type'] = 'event'
            response_context['event_type'] = message_type

        if not should_respond:
            logger.audit(
                action="process_interaction",
                user=username,
                community=entity_id,
                result="NO_RESPONSE_NEEDED",
                message_type=message_type
            )
            return

        # Generate AI response
        ai_response = await ai_service.generate_response(
            message_content=message_content,
            message_type=message_type,
            user_id=user_id,
            platform=platform,
            context=response_context
        )

        # Calculate processing time
        processing_time = int(  # noqa: E501
            (datetime.utcnow() - start_time).total_seconds() * 1000
        )

        if ai_response:
            # Send response back to router
            response_data = {
                "session_id": session_id,
                "module_name": Config.MODULE_NAME,
                "success": True,
                "response_action": "chat",
                "response_data": {
                    "message": f"{Config.RESPONSE_PREFIX}{ai_response}"
                },
                "processing_time_ms": processing_time
            }

            await router_service.submit_response(response_data)

            logger.audit(
                action="process_interaction",
                user=username,
                community=entity_id,
                result="SUCCESS",
                execution_time=processing_time
            )
        else:
            logger.error(
                "No AI response generated",
                user=username,
                community=entity_id,
                action="generate_response"
            )

    except Exception as e:
        logger.error(
            f"Error processing interaction: {e}",
            user=username,
            community=entity_id,
            action="process_interaction"
        )

        # Send error response to router
        error_response_data = {
            "session_id": session_id,
            "module_name": Config.MODULE_NAME,
            "success": False,
            "error_message": str(e),
            "processing_time_ms": int(  # noqa: E501
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
        }

        try:
            await router_service.submit_response(error_response_data)
        except Exception as submit_error:
            logger.error(  # noqa: E501
                f"Failed to submit error response: {submit_error}"
            )


# OpenAI-compatible chat completions endpoint
@ai_bp.route('/chat/completions', methods=['POST'])
@auth_required
@async_endpoint
async def chat_completions():
    """
    OpenAI-compatible chat completions endpoint.

    Compatible with OpenAI API format for easy integration.
    Note: Validation is done manually here to maintain OpenAI API
    compatibility (arbitrary message shape, not the fixed ChatRequest
    schema) -- but every message's content still goes through the same
    sanitize_input() guard ChatRequest/InteractionRequest apply, it's just
    invoked directly instead of via @validate_json. regression:
    sec-llm01-audit
    """
    try:
        data = await request.get_json()

        if not data:
            return error_response(
                "Request body must be valid JSON", status_code=400
            )

        messages = data.get('messages', [])
        model = data.get('model', Config.AI_MODEL)
        # Note: temperature and max_tokens from request not currently used
        # but kept for OpenAI API compatibility
        _ = data.get('temperature', Config.AI_TEMPERATURE)  # noqa: F841
        _ = data.get('max_tokens', Config.AI_MAX_TOKENS)  # noqa: F841

        if not messages:
            return error_response(  # noqa: E501
                "messages array is required", status_code=400
            )

        if not isinstance(messages, list):
            return error_response(
                "messages must be an array", status_code=400
            )

        if len(messages) > 50:
            return error_response(
                "messages array cannot exceed 50 items", status_code=400
            )

        # Sanitize every message's content with the same guard
        # InteractionRequest/ChatRequest apply to user-supplied text
        # (flask_core.sanitization.sanitize_input) -- this endpoint parses
        # messages manually to preserve OpenAI API shape compatibility, so
        # @validate_json(ChatRequest) can't be reused directly, but the
        # sanitizer step it depends on must not be skipped.
        # regression: sec-llm01-audit
        sanitized_messages = []
        for msg in messages:
            if not isinstance(msg, dict):
                return error_response(
                    "each message must be an object", status_code=400
                )
            content = msg.get('content', '')
            if isinstance(content, str):
                content = sanitize_input(content, allow_html=False)
            sanitized_messages.append({**msg, 'content': content})
        messages = sanitized_messages

        # Extract last user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break

        # Build context from messages
        context = {
            'conversation_history': messages[:-1] if len(messages) > 1 else [],
            'trigger_type': 'api_request'
        }

        # Generate response
        ai_response = await ai_service.generate_response(
            message_content=user_message,
            message_type='chatMessage',
            user_id=request.current_user['user_id'],
            platform='api',
            context=context
        )

        if ai_response:
            # OpenAI-compatible response format
            user_id = request.current_user['user_id']
            return success_response({
                "id": f"chatcmpl-{user_id}",
                "object": "chat.completion",
                "created": int(datetime.utcnow().timestamp()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ai_response
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(user_message.split()),
                    "completion_tokens": len(ai_response.split()),
                    "total_tokens": (  # noqa: E501
                        len(user_message.split()) +
                        len(ai_response.split())
                    )
                }
            })
        else:
            return error_response(  # noqa: E501
                "Failed to generate response", status_code=500
            )

    except Exception as e:
        logger.error(f"Chat completions error: {e}")
        return error_response(str(e), status_code=500)


# Get available models
@ai_bp.route('/models', methods=['GET'])
@async_endpoint
async def get_models():
    """Get list of available AI models"""
    try:
        models = await ai_service.get_available_models()

        return success_response({
            "provider": Config.AI_PROVIDER,
            "models": models,
            "current_model": Config.AI_MODEL
        })

    except Exception as e:
        logger.error(f"Get models error: {e}")
        return error_response(str(e), status_code=500)


# Get/Update configuration
@ai_bp.route('/config', methods=['GET'])
@auth_required
@async_endpoint
async def get_config():
    """Get AI module configuration"""
    try:
        # Return current configuration
        return success_response({
            "provider": Config.AI_PROVIDER,
            "model": Config.AI_MODEL,
            "temperature": Config.AI_TEMPERATURE,
            "max_tokens": Config.AI_MAX_TOKENS,
            "system_prompt": Config.SYSTEM_PROMPT,
            "question_triggers": Config.QUESTION_TRIGGERS,
            "respond_to_events": Config.RESPOND_TO_EVENTS,
            "event_response_types": Config.EVENT_RESPONSE_TYPES
        })

    except Exception as e:
        logger.error(f"Config endpoint error: {e}")
        return error_response(str(e), status_code=500)


@ai_bp.route('/config', methods=['PUT'])
@auth_required
@validate_json(ProviderConfigRequest)
@async_endpoint
async def update_config(validated_data: ProviderConfigRequest):
    """Update AI module configuration with validation"""
    try:
        # Update configuration with validated data
        if validated_data.model is not None:
            Config.AI_MODEL = validated_data.model
        if validated_data.temperature is not None:
            Config.AI_TEMPERATURE = validated_data.temperature
        if validated_data.max_tokens is not None:
            Config.AI_MAX_TOKENS = validated_data.max_tokens
        if validated_data.system_prompt is not None:
            Config.SYSTEM_PROMPT = validated_data.system_prompt

        # Note: api_key and base_url would be stored in database
        # in production, not in Config

        logger.audit(
            action="update_config",
            user=request.current_user['username'],
            community=str(validated_data.community_id),
            result="SUCCESS"
        )

        return success_response({
            "message": "Configuration updated successfully",
            "config": {
                "provider": Config.AI_PROVIDER,
                "model": Config.AI_MODEL,
                "temperature": Config.AI_TEMPERATURE,
                "max_tokens": Config.AI_MAX_TOKENS
            }
        })

    except Exception as e:
        logger.error(f"Config endpoint error: {e}")
        return error_response(str(e), status_code=500)


# Test endpoint
@ai_bp.route('/test', methods=['POST'])
@auth_required
@async_endpoint
async def test():
    """Test AI generation with custom input"""
    try:
        data = await request.get_json()

        if not data:
            return error_response(
                "Request body must be valid JSON", status_code=400
            )

        test_message = data.get('message', 'What is the weather like?')

        # Validate message length
        if len(test_message) > 10000:
            return error_response(
                "message cannot exceed 10000 characters", status_code=400
            )

        response_text = await ai_service.generate_response(
            message_content=test_message,
            message_type='chatMessage',
            user_id=request.current_user['user_id'],
            platform='test',
            context={'trigger_type': 'test'}
        )

        return success_response({
            "input": test_message,
            "output": response_text,
            "provider": Config.AI_PROVIDER,
            "model": Config.AI_MODEL
        })

    except Exception as e:
        logger.error(f"Test endpoint error: {e}")
        return error_response(str(e), status_code=500)


@ai_bp.route('/proactive-chat', methods=['POST'])
@async_endpoint
async def proactive_chat():
    """
    Proactive chat endpoint -- called by router when community has AIChatter enabled.
    Checks config, rate limits, probability, then generates response if appropriate.

    Expected JSON:
    {
        "session_id": str,
        "community_id": int,
        "user_id": str,
        "platform_user_id": str,
        "message": str,
        "platform": str,
        "channel_id": str
    }
    """
    try:
        data = await request.get_json()
        if not data:
            return error_response("Request body must be valid JSON", status_code=400)

        community_id = data.get('community_id')
        user_id = data.get('user_id', '')
        message = data.get('message', '')
        session_id = data.get('session_id', '')

        if not community_id or not message:
            return error_response("community_id and message are required", status_code=400)

        community_id = int(community_id)

        # Get community config
        config = await chatter_config_service.get_community_config(community_id)
        if not config or not config.get('enabled', False):
            return success_response({'responded': False, 'reason': 'disabled'})

        # Fire-and-forget: check rate limits, probability, and generate response
        asyncio.create_task(
            _handle_proactive_chat(
                session_id, community_id, user_id, message, config,
                data.get('platform', 'unknown'), data.get('channel_id', '')
            )
        )

        return success_response({'responded': True, 'queued': True})

    except Exception as e:
        logger.error(f"Proactive chat endpoint error: {e}")
        return error_response(str(e), status_code=500)


async def _handle_proactive_chat(
    session_id: str,
    community_id: int,
    user_id: str,
    message: str,
    config: dict,
    platform: str,
    channel_id: str,
):
    """Fire-and-forget proactive chat handler."""
    start_time = datetime.utcnow()
    try:
        should_respond = await proactive_chat_service.should_respond(
            community_id=community_id,
            user_id=user_id,
            message=message,
            config=config,
        )

        if not should_respond:
            return

        ai_response = await proactive_chat_service.generate_response(
            message=message,
            community_id=community_id,
            user_id=user_id,
            session_id=session_id,
        )

        if ai_response:
            processing_time = int(
                (datetime.utcnow() - start_time).total_seconds() * 1000
            )
            response_data = {
                'session_id': session_id,
                'module_name': Config.MODULE_NAME,
                'success': True,
                'response_action': 'chat',
                'response_data': {'message': ai_response},
                'processing_time_ms': processing_time,
            }
            await router_service.submit_response(response_data)

            logger.audit(
                action="proactive_chat_response",
                community=str(community_id),
                user=user_id,
                result="SUCCESS",
                execution_time=processing_time,
            )

    except Exception as e:
        logger.error(
            f"Proactive chat handling error: {e}",
            community_id=community_id,
            user_id=user_id,
        )


@ai_bp.route('/config/chatter', methods=['GET'])
@async_endpoint
async def get_chatter_config():
    """
    Get community AIChatter config. Called from hub admin panel.
    Requires X-Community-ID header or community_id query param.
    """
    try:
        community_id_str = (
            request.headers.get('X-Community-ID') or
            request.args.get('community_id')
        )
        if not community_id_str:
            return error_response(
                "X-Community-ID header or community_id param required",
                status_code=400
            )
        community_id = int(community_id_str)
        config = await chatter_config_service.get_community_config(community_id)
        if config is None:
            # Return defaults if no config exists
            config = {
                'enabled': False,
                'max_responses_per_window': 10,
                'window_seconds': 600,
                'max_per_user_per_window': 2,
                'response_probability': 0.30,
                'min_message_length': 10,
            }
        return success_response(config)
    except Exception as e:
        logger.error(f"Get chatter config error: {e}")
        return error_response(str(e), status_code=500)


@ai_bp.route('/config/chatter', methods=['POST'])
@async_endpoint
async def update_chatter_config():
    """
    Update community AIChatter config. Called from hub admin panel.
    Validates all fields before saving.
    """
    try:
        data = await request.get_json()
        if not data:
            return error_response("Request body must be valid JSON", status_code=400)

        community_id_str = data.get('community_id') or request.headers.get('X-Community-ID')
        if not community_id_str:
            return error_response("community_id required", status_code=400)
        community_id = int(community_id_str)

        # Validate and collect settings
        settings = {}
        if 'enabled' in data:
            settings['enabled'] = bool(data['enabled'])
        if 'max_responses_per_window' in data:
            v = int(data['max_responses_per_window'])
            if not 1 <= v <= 100:
                return error_response(
                    "max_responses_per_window must be 1-100", status_code=400
                )
            settings['max_responses_per_window'] = v
        if 'window_seconds' in data:
            v = int(data['window_seconds'])
            if not 60 <= v <= 3600:
                return error_response(
                    "window_seconds must be 60-3600", status_code=400
                )
            settings['window_seconds'] = v
        if 'max_per_user_per_window' in data:
            v = int(data['max_per_user_per_window'])
            if not 1 <= v <= 20:
                return error_response(
                    "max_per_user_per_window must be 1-20", status_code=400
                )
            settings['max_per_user_per_window'] = v
        if 'response_probability' in data:
            v = float(data['response_probability'])
            if not 0.05 <= v <= 1.0:
                return error_response(
                    "response_probability must be 0.05-1.0", status_code=400
                )
            settings['response_probability'] = v
        if 'min_message_length' in data:
            v = int(data['min_message_length'])
            if v < 0:
                return error_response(
                    "min_message_length must be >= 0", status_code=400
                )
            settings['min_message_length'] = v

        updated = await chatter_config_service.update_community_config(community_id, settings)
        return success_response(updated)
    except Exception as e:
        logger.error(f"Update chatter config error: {e}")
        return error_response(str(e), status_code=500)


# Register blueprint
app.register_blueprint(ai_bp)


if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config as HyperConfig

    hyper_config = HyperConfig()
    hyper_config.bind = [f"0.0.0.0:{Config.MODULE_PORT}"]
    asyncio.run(hypercorn.asyncio.serve(app, hyper_config))
