#!/usr/bin/env python3
import os
import sys
from py4web import action, request, response, Field, HTTP
from py4web.core import Fixture
import json
import asyncio
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor

# Add the parent directory to the path to import libs
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from services.ai_service import AIService
from services.router_service import RouterService

# Import API controller
import controllers.api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
ai_service = AIService()
router_service = RouterService()
executor = ThreadPoolExecutor(max_workers=Config.MAX_CONCURRENT_REQUESTS)

class AuthFixture(Fixture):
    """Simple auth fixture for API endpoints"""
    def on_request(self, context):
        # For now, allow all requests - can add auth later
        pass

auth = AuthFixture()

@action('index')
@action.uses('index.html')
def index():
    """Health check endpoint"""
    return dict(
        module=Config.MODULE_NAME,
        version=Config.MODULE_VERSION,
        status="healthy",
        ai_provider=Config.AI_PROVIDER,
        ai_host=Config.AI_HOST,
        model=Config.AI_MODEL
    )

@action('health')
def health():
    """Health check for container orchestration"""
    try:
        # Test AI provider connection
        health_status = ai_service.health_check()
        if health_status:
            response.status = 200
            return {"status": "healthy", "ai_provider": Config.AI_PROVIDER, "connection": "connected"}
        else:
            response.status = 503
            return {"status": "unhealthy", "ai_provider": Config.AI_PROVIDER, "connection": "disconnected"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        response.status = 503
        return {"status": "unhealthy", "error": str(e)}

@action('interaction', method=['POST'])
@action.uses(auth)
def interaction():
    """Main interaction endpoint for processing messages and events"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No JSON data provided")
        
        # Extract required fields
        session_id = data.get('session_id')
        message_type = data.get('message_type', 'chatMessage')
        message_content = data.get('message_content', '')
        user_id = data.get('user_id')
        entity_id = data.get('entity_id')
        platform = data.get('platform')
        
        if not session_id:
            raise HTTP(400, "session_id is required")
        
        logger.info(f"Processing {message_type} from user {user_id} on {platform}")
        
        # Process asynchronously
        future = executor.submit(
            process_interaction_sync,
            session_id, message_type, message_content, user_id, entity_id, platform, data
        )
        
        # Return immediate response
        return {
            "success": True,
            "message": "Processing request",
            "session_id": session_id
        }
        
    except Exception as e:
        logger.error(f"Error in interaction endpoint: {str(e)}\n{traceback.format_exc()}")
        raise HTTP(500, f"Internal server error: {str(e)}")

def process_interaction_sync(session_id, message_type, message_content, user_id, entity_id, platform, full_data):
    """Synchronous wrapper for async processing"""
    try:
        # Determine if we should respond
        should_respond = False
        response_context = {}
        
        if message_type == 'chatMessage':
            # Check for greeting patterns
            greeting_patterns = ['o7', 'hi', 'hello', 'hey', 'howdy', 'greetings', 'sup', 'hiya', 'morning', 'evening', 'afternoon']
            farewell_patterns = ['!lurk', 'bye', 'goodbye', 'later', 'cya', 'see ya', 'take care', 'gotta go', 'gtg', 'peace out', 'catch you later']
            
            message_lower = message_content.lower().strip()
            
            # Check for greetings
            for pattern in greeting_patterns:
                if pattern in message_lower or message_lower == pattern:
                    should_respond = True
                    response_context['trigger_type'] = 'greeting'
                    response_context['trigger'] = pattern
                    break
            
            # Check for farewells
            if not should_respond:
                for pattern in farewell_patterns:
                    if pattern in message_lower or message_lower == pattern:
                        should_respond = True
                        response_context['trigger_type'] = 'farewell'
                        response_context['trigger'] = pattern
                        break
            
            # Check for question triggers
            if not should_respond:
                for trigger in Config.QUESTION_TRIGGERS:
                    if trigger in message_content:
                        should_respond = True
                        response_context['trigger_type'] = 'question'
                        response_context['trigger'] = trigger
                        break
        elif message_type in Config.EVENT_RESPONSE_TYPES and Config.RESPOND_TO_EVENTS:
            should_respond = True
            response_context['trigger_type'] = 'event'
            response_context['event_type'] = message_type
        
        if not should_respond:
            logger.info(f"No response needed for {message_type}: {message_content}")
            return
        
        # Generate response using AI service
        ai_response = ai_service.generate_response(
            message_content=message_content,
            message_type=message_type,
            user_id=user_id,
            platform=platform,
            context=response_context
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
                "processing_time_ms": 0  # Could track this if needed
            }
            
            router_service.submit_response(response_data)
            logger.info(f"Sent AI response for session {session_id}")
        else:
            logger.warning(f"No AI response generated for session {session_id}")
            
    except Exception as e:
        logger.error(f"Error processing interaction: {str(e)}\n{traceback.format_exc()}")
        
        # Send error response back to router
        error_response = {
            "session_id": session_id,
            "module_name": Config.MODULE_NAME,
            "success": False,
            "error_message": str(e),
            "processing_time_ms": 0
        }
        
        try:
            router_service.submit_response(error_response)
        except Exception as submit_error:
            logger.error(f"Failed to submit error response: {str(submit_error)}")

@action('configure', method=['POST'])
@action.uses(auth)
def configure():
    """Configure module settings"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No JSON data provided")
        
        # Update configuration dynamically
        if 'provider' in data:
            Config.AI_PROVIDER = data['provider']
            # Reinitialize AI service with new provider
            global ai_service
            ai_service = AIService()
        if 'model' in data:
            Config.AI_MODEL = data['model']
            ai_service.update_model(data['model'])
        if 'temperature' in data:
            Config.AI_TEMPERATURE = float(data['temperature'])
        if 'max_tokens' in data:
            Config.AI_MAX_TOKENS = int(data['max_tokens'])
        if 'system_prompt' in data:
            Config.SYSTEM_PROMPT = data['system_prompt']
        if 'question_triggers' in data:
            Config.QUESTION_TRIGGERS = data['question_triggers']
        if 'respond_to_events' in data:
            Config.RESPOND_TO_EVENTS = bool(data['respond_to_events'])
        if 'event_response_types' in data:
            Config.EVENT_RESPONSE_TYPES = data['event_response_types']
        
        return {
            "success": True,
            "message": "Configuration updated",
            "config": {
                "provider": Config.AI_PROVIDER,
                "model": Config.AI_MODEL,
                "temperature": Config.AI_TEMPERATURE,
                "max_tokens": Config.AI_MAX_TOKENS,
                "system_prompt": Config.SYSTEM_PROMPT,
                "question_triggers": Config.QUESTION_TRIGGERS,
                "respond_to_events": Config.RESPOND_TO_EVENTS,
                "event_response_types": Config.EVENT_RESPONSE_TYPES
            }
        }
        
    except Exception as e:
        logger.error(f"Error in configure endpoint: {str(e)}")
        raise HTTP(500, f"Configuration error: {str(e)}")

@action('test', method=['POST'])
@action.uses(auth)
def test():
    """Test endpoint for debugging"""
    try:
        data = request.json
        test_message = data.get('message', 'What is the weather like?')
        
        response_text = ai_service.generate_response(
            message_content=test_message,
            message_type='chatMessage',
            user_id='test_user',
            platform='test',
            context={'trigger_type': 'question', 'trigger': '?'}
        )
        
        return {
            "success": True,
            "input": test_message,
            "output": response_text,
            "provider": Config.AI_PROVIDER,
            "model": Config.AI_MODEL
        }
        
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        raise HTTP(500, f"Test error: {str(e)}")

if __name__ == "__main__":
    import py4web
    py4web.main()