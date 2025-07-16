import logging
import requests
import json
from typing import Optional, Dict, Any
import traceback

from config import Config
from .ai_service import AIProvider

logger = logging.getLogger(__name__)


class MCPProvider(AIProvider):
    """Model Context Protocol (MCP) provider implementation"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.timeout = Config.MCP_TIMEOUT
        self.conversation_history = {}  # Simple in-memory conversation storage
        
        # Set headers for MCP requests
        if Config.AI_API_KEY:
            self.session.headers.update({
                'Authorization': f'Bearer {Config.AI_API_KEY}',
                'Content-Type': 'application/json'
            })
    
    def health_check(self) -> bool:
        """Check if MCP server is available"""
        try:
            # Try to ping the MCP server health endpoint
            health_url = f"{Config.MCP_SERVER_URL}/health"
            response = self.session.get(health_url, timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {str(e)}")
            return False
    
    def generate_response(self, message_content: str, message_type: str, 
                         user_id: str, platform: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI response using MCP server"""
        try:
            # Build the request payload
            payload = self._build_mcp_payload(message_content, message_type, user_id, platform, context)
            
            # Send request to MCP server
            logger.info(f"Sending MCP request for user {user_id}")
            response = self.session.post(
                f"{Config.MCP_SERVER_URL}/chat/completions",
                json=payload,
                timeout=Config.MCP_TIMEOUT
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Extract the generated text
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    content = response_data['choices'][0].get('message', {}).get('content', '')
                    
                    # Store conversation history if enabled
                    if Config.ENABLE_CHAT_CONTEXT:
                        self._update_conversation_history(user_id, message_content, content)
                    
                    # Clean and validate response
                    cleaned_response = self._clean_response(content)
                    logger.info(f"Generated MCP response: {cleaned_response}")
                    
                    return cleaned_response
                
                # Try alternative response format
                elif 'response' in response_data:
                    content = response_data['response']
                    cleaned_response = self._clean_response(content)
                    logger.info(f"Generated MCP response: {cleaned_response}")
                    return cleaned_response
            
            else:
                logger.error(f"MCP server returned status {response.status_code}: {response.text}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating MCP response: {str(e)}\n{traceback.format_exc()}")
            return None
    
    def get_available_models(self) -> list:
        """Get list of available models from MCP server"""
        try:
            models_url = f"{Config.MCP_SERVER_URL}/models"
            response = self.session.get(models_url, timeout=5)
            
            if response.status_code == 200:
                models_data = response.json()
                
                # Handle different response formats
                if 'data' in models_data:
                    return [model['id'] for model in models_data['data']]
                elif 'models' in models_data:
                    return models_data['models']
                elif isinstance(models_data, list):
                    return models_data
                
            return []
        except Exception as e:
            logger.error(f"Failed to get available MCP models: {str(e)}")
            return []
    
    def _build_mcp_payload(self, message_content: str, message_type: str, 
                          user_id: str, platform: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build payload for MCP server request"""
        
        # Build messages similar to OpenAI format (many MCP servers follow this)
        messages = [
            {"role": "system", "content": Config.SYSTEM_PROMPT}
        ]
        
        # Add conversation history if enabled
        if Config.ENABLE_CHAT_CONTEXT and user_id in self.conversation_history:
            history = self.conversation_history[user_id]
            # Add last few exchanges
            for exchange in history[-Config.CONTEXT_HISTORY_LIMIT:]:
                messages.append({"role": "user", "content": exchange['user']})
                messages.append({"role": "assistant", "content": exchange['assistant']})
        
        # Add current message based on type
        if message_type == 'chatMessage':
            user_message = f"Platform: {platform}\nUser {user_id}: {message_content}"
        else:
            user_message = self._create_event_message(message_type, user_id, platform, context)
        
        messages.append({"role": "user", "content": user_message})
        
        # Build the payload
        payload = {
            "model": Config.AI_MODEL,
            "messages": messages,
            "temperature": Config.AI_TEMPERATURE,
            "max_tokens": Config.AI_MAX_TOKENS,
            "user": user_id,
            "metadata": {
                "platform": platform,
                "message_type": message_type,
                "context": context
            }
        }
        
        return payload
    
    def _create_event_message(self, message_type: str, user_id: str, 
                             platform: str, context: Dict[str, Any]) -> str:
        """Create message for event responses"""
        
        event_messages = {
            'subscription': f"User {user_id} just subscribed on {platform}! Generate a celebratory thank you message.",
            'follow': f"User {user_id} just followed on {platform}! Generate a welcoming thank you message.",
            'donation': f"User {user_id} just made a donation on {platform}! Generate a grateful thank you message.",
            'cheer': f"User {user_id} just sent bits/cheered on {platform}! Generate an excited thank you message.",
            'raid': f"User {user_id} just raided the channel on {platform}! Generate a welcoming message for the raiders.",
            'boost': f"User {user_id} just boosted the server on {platform}! Generate a thank you message for the boost.",
            'member_join': f"User {user_id} just joined on {platform}! Generate a welcoming message."
        }
        
        return event_messages.get(
            message_type, 
            f"User {user_id} triggered a {message_type} event on {platform}! Generate an appropriate response."
        )
    
    def _update_conversation_history(self, user_id: str, user_message: str, assistant_response: str):
        """Update conversation history for context"""
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        
        self.conversation_history[user_id].append({
            'user': user_message,
            'assistant': assistant_response
        })
        
        # Keep only recent conversations to avoid memory issues
        if len(self.conversation_history[user_id]) > Config.CONTEXT_HISTORY_LIMIT * 2:
            self.conversation_history[user_id] = self.conversation_history[user_id][-Config.CONTEXT_HISTORY_LIMIT:]
    
    def _clean_response(self, response: str) -> str:
        """Clean and validate the AI response"""
        if not response:
            return ""
        
        # Remove any potential prompt injection or unwanted content
        cleaned = response.strip()
        
        # Remove any system prompts that might have leaked through
        if cleaned.lower().startswith("you are"):
            lines = cleaned.split('\n')
            for i, line in enumerate(lines):
                if not line.lower().startswith("you are") and line.strip():
                    cleaned = '\n'.join(lines[i:])
                    break
        
        # Limit length for chat readability
        if len(cleaned) > 400:
            cleaned = cleaned[:397] + "..."
        
        return cleaned