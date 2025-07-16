#!/usr/bin/env python3
"""
AI Interaction Module API Controller
Provides REST API endpoints for other WaddleBot modules to access AI services
"""

import logging
import time
import traceback
from py4web import action, request, response, HTTP
from py4web.core import Fixture
import json
from typing import Dict, Any, Optional

from config import Config
from services.ai_service import AIService

# Configure logging
logger = logging.getLogger(__name__)

# Initialize AI service
ai_service = AIService()

class APIKeyAuthFixture(Fixture):
    """API Key authentication fixture for external module access"""
    
    def on_request(self, context):
        # Check for API key in headers or query params
        api_key = request.headers.get('X-API-Key') or request.query.get('apikey')
        
        if not api_key:
            raise HTTP(401, "API key required")
        
        # For now, accept any non-empty key - integrate with Kong auth
        # Kong will handle the actual authentication before requests reach here
        context['api_key'] = api_key
        context['authenticated'] = True

api_auth = APIKeyAuthFixture()

@action('api/v1/chat/completions', method=['POST'])
@action.uses(api_auth)
def chat_completions():
    """
    OpenAI-compatible chat completions endpoint
    Allows other modules to send chat requests using OpenAI format
    """
    start_time = time.time()
    
    try:
        data = request.json
        if not data:
            raise HTTP(400, "Request body is required")
        
        # Extract OpenAI-style parameters
        messages = data.get('messages', [])
        model = data.get('model', Config.AI_MODEL)
        temperature = data.get('temperature', Config.AI_TEMPERATURE)
        max_tokens = data.get('max_tokens', Config.AI_MAX_TOKENS)
        user_id = data.get('user', 'api_user')
        
        # Validate messages format
        if not messages or not isinstance(messages, list):
            raise HTTP(400, "Messages array is required")
        
        # Extract the user message (last message typically)
        user_message = ""
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                user_message = msg.get('content', '')
                break
        
        if not user_message:
            raise HTTP(400, "No user message found in messages array")
        
        # Temporarily update config for this request
        original_model = Config.AI_MODEL
        original_temp = Config.AI_TEMPERATURE
        original_tokens = Config.AI_MAX_TOKENS
        
        Config.AI_MODEL = model
        Config.AI_TEMPERATURE = temperature
        Config.AI_MAX_TOKENS = max_tokens
        
        try:
            # Generate AI response
            ai_response = ai_service.generate_response(
                message_content=user_message,
                message_type='chatMessage',
                user_id=user_id,
                platform='api',
                context={'trigger_type': 'api', 'api_request': True}
            )
        finally:
            # Restore original config
            Config.AI_MODEL = original_model
            Config.AI_TEMPERATURE = original_temp
            Config.AI_MAX_TOKENS = original_tokens
        
        if ai_response is None:
            raise HTTP(500, "Failed to generate AI response")
        
        # Return OpenAI-compatible format
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": ai_response
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(user_message.split()),
                "completion_tokens": len(ai_response.split()),
                "total_tokens": len(user_message.split()) + len(ai_response.split())
            },
            "metadata": {
                "provider": Config.AI_PROVIDER,
                "processing_time_ms": processing_time
            }
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in chat completions: {str(e)}\n{traceback.format_exc()}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/generate', method=['POST'])
@action.uses(api_auth)
def generate_text():
    """
    Simple text generation endpoint
    Accepts a prompt and returns generated text
    """
    start_time = time.time()
    
    try:
        data = request.json
        if not data:
            raise HTTP(400, "Request body is required")
        
        prompt = data.get('prompt', '')
        user_id = data.get('user_id', 'api_user')
        platform = data.get('platform', 'api')
        model = data.get('model', Config.AI_MODEL)
        temperature = data.get('temperature', Config.AI_TEMPERATURE)
        max_tokens = data.get('max_tokens', Config.AI_MAX_TOKENS)
        
        if not prompt:
            raise HTTP(400, "Prompt is required")
        
        # Temporarily update config for this request
        original_model = Config.AI_MODEL
        original_temp = Config.AI_TEMPERATURE
        original_tokens = Config.AI_MAX_TOKENS
        
        Config.AI_MODEL = model
        Config.AI_TEMPERATURE = temperature
        Config.AI_MAX_TOKENS = max_tokens
        
        try:
            # Generate AI response
            ai_response = ai_service.generate_response(
                message_content=prompt,
                message_type='chatMessage',
                user_id=user_id,
                platform=platform,
                context={'trigger_type': 'api', 'api_request': True}
            )
        finally:
            # Restore original config
            Config.AI_MODEL = original_model
            Config.AI_TEMPERATURE = original_temp
            Config.AI_MAX_TOKENS = original_tokens
        
        if ai_response is None:
            raise HTTP(500, "Failed to generate AI response")
        
        processing_time = (time.time() - start_time) * 1000
        
        return {
            "success": True,
            "prompt": prompt,
            "generated_text": ai_response,
            "metadata": {
                "provider": Config.AI_PROVIDER,
                "model": model,
                "processing_time_ms": processing_time,
                "user_id": user_id,
                "platform": platform
            }
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error in generate text: {str(e)}\n{traceback.format_exc()}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action('api/v1/models', method=['GET'])
@action.uses(api_auth)
def list_models():
    """
    List available AI models
    """
    try:
        available_models = ai_service.get_available_models()
        
        return {
            "object": "list",
            "data": [
                {
                    "id": model,
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": Config.AI_PROVIDER,
                    "provider": Config.AI_PROVIDER
                }
                for model in available_models
            ],
            "current_model": Config.AI_MODEL,
            "current_provider": Config.AI_PROVIDER
        }
        
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTP(500, f"Failed to list models: {str(e)}")

@action('api/v1/health', method=['GET'])
def api_health():
    """
    API health check endpoint (no auth required)
    """
    try:
        ai_health = ai_service.health_check()
        
        return {
            "status": "healthy" if ai_health else "unhealthy",
            "provider": Config.AI_PROVIDER,
            "model": Config.AI_MODEL,
            "ai_service": "connected" if ai_health else "disconnected",
            "timestamp": int(time.time())
        }
        
    except Exception as e:
        logger.error(f"API health check failed: {str(e)}")
        response.status = 503
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": int(time.time())
        }

@action('api/v1/config', method=['GET'])
@action.uses(api_auth)
def get_config():
    """
    Get current AI configuration
    """
    try:
        return {
            "provider": Config.AI_PROVIDER,
            "model": Config.AI_MODEL,
            "temperature": Config.AI_TEMPERATURE,
            "max_tokens": Config.AI_MAX_TOKENS,
            "system_prompt": Config.SYSTEM_PROMPT,
            "question_triggers": Config.QUESTION_TRIGGERS,
            "response_prefix": Config.RESPONSE_PREFIX,
            "context_enabled": Config.ENABLE_CHAT_CONTEXT,
            "context_limit": Config.CONTEXT_HISTORY_LIMIT,
            "event_responses": Config.RESPOND_TO_EVENTS,
            "event_types": Config.EVENT_RESPONSE_TYPES
        }
        
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        raise HTTP(500, f"Failed to get config: {str(e)}")

@action('api/v1/config', method=['PUT'])
@action.uses(api_auth)
def update_config():
    """
    Update AI configuration
    """
    try:
        data = request.json
        if not data:
            raise HTTP(400, "Request body is required")
        
        updated_fields = []
        
        # Update provider if specified
        if 'provider' in data:
            if data['provider'] in ['ollama', 'openai', 'mcp']:
                Config.AI_PROVIDER = data['provider']
                # Reinitialize AI service with new provider
                global ai_service
                ai_service = AIService()
                updated_fields.append('provider')
            else:
                raise HTTP(400, "Invalid provider. Must be 'ollama', 'openai', or 'mcp'")
        
        # Update other configuration fields
        config_mapping = {
            'model': ('AI_MODEL', str),
            'temperature': ('AI_TEMPERATURE', float),
            'max_tokens': ('AI_MAX_TOKENS', int),
            'system_prompt': ('SYSTEM_PROMPT', str),
            'question_triggers': ('QUESTION_TRIGGERS', list),
            'response_prefix': ('RESPONSE_PREFIX', str),
            'context_enabled': ('ENABLE_CHAT_CONTEXT', bool),
            'context_limit': ('CONTEXT_HISTORY_LIMIT', int),
            'event_responses': ('RESPOND_TO_EVENTS', bool),
            'event_types': ('EVENT_RESPONSE_TYPES', list)
        }
        
        for field, (config_attr, field_type) in config_mapping.items():
            if field in data:
                try:
                    if field_type == list:
                        value = data[field] if isinstance(data[field], list) else [data[field]]
                    else:
                        value = field_type(data[field])
                    
                    setattr(Config, config_attr, value)
                    updated_fields.append(field)
                    
                    # Special handling for model updates
                    if field == 'model':
                        ai_service.update_model(value)
                        
                except (ValueError, TypeError) as e:
                    raise HTTP(400, f"Invalid value for {field}: {str(e)}")
        
        if not updated_fields:
            raise HTTP(400, "No valid configuration fields provided")
        
        return {
            "success": True,
            "message": f"Updated configuration fields: {', '.join(updated_fields)}",
            "updated_fields": updated_fields,
            "current_config": {
                "provider": Config.AI_PROVIDER,
                "model": Config.AI_MODEL,
                "temperature": Config.AI_TEMPERATURE,
                "max_tokens": Config.AI_MAX_TOKENS
            }
        }
        
    except HTTP:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        raise HTTP(500, f"Failed to update config: {str(e)}")

@action('api/v1/providers', method=['GET'])
@action.uses(api_auth)
def list_providers():
    """
    List available AI providers and their status
    """
    try:
        providers = {
            'ollama': {
                'name': 'Ollama',
                'description': 'Local LLM hosting with LangChain integration',
                'status': 'available',
                'config_required': ['AI_HOST', 'AI_MODEL']
            },
            'openai': {
                'name': 'OpenAI',
                'description': 'OpenAI API integration',
                'status': 'available',
                'config_required': ['OPENAI_API_KEY', 'OPENAI_MODEL']
            },
            'mcp': {
                'name': 'Model Context Protocol',
                'description': 'Standardized AI model communication protocol',
                'status': 'available',
                'config_required': ['MCP_SERVER_URL', 'AI_MODEL']
            }
        }
        
        # Check current provider health
        current_provider = Config.AI_PROVIDER
        if current_provider in providers:
            try:
                health = ai_service.health_check()
                providers[current_provider]['health'] = 'healthy' if health else 'unhealthy'
                providers[current_provider]['current'] = True
            except:
                providers[current_provider]['health'] = 'error'
                providers[current_provider]['current'] = True
        
        return {
            "providers": providers,
            "current_provider": current_provider
        }
        
    except Exception as e:
        logger.error(f"Error listing providers: {str(e)}")
        raise HTTP(500, f"Failed to list providers: {str(e)}")