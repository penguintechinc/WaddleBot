import logging
import openai
from typing import Optional, Dict, Any, List
import traceback

from config import Config
from .ai_service import AIProvider

logger = logging.getLogger(__name__)


class OpenAIProvider(AIProvider):
    """OpenAI API provider implementation"""
    
    def __init__(self):
        self.client = None
        self.conversation_history = {}  # Simple in-memory conversation storage
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the OpenAI client"""
        try:
            api_key = Config.AI_API_KEY or Config.OPENAI_API_KEY
            if not api_key:
                raise ValueError("OpenAI API key is required but not provided")
            
            # Configure OpenAI client
            openai.api_key = api_key
            
            # Use base URL if provided (for compatible APIs)
            if Config.OPENAI_BASE_URL and Config.OPENAI_BASE_URL != 'https://api.openai.com/v1':
                openai.base_url = Config.OPENAI_BASE_URL
                
            self.client = openai.OpenAI(
                api_key=api_key,
                base_url=Config.OPENAI_BASE_URL
            )
            
            logger.info(f"Initialized OpenAI client with base URL: {Config.OPENAI_BASE_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """Check if OpenAI API is available"""
        try:
            if not self.client:
                self.initialize_client()
                
            # Try to list models as a health check
            self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {str(e)}")
            return False
    
    def generate_response(self, message_content: str, message_type: str, 
                         user_id: str, platform: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI response using OpenAI"""
        try:
            if not self.client:
                self.initialize_client()
            
            # Build messages for the conversation
            messages = self._build_messages(message_content, message_type, user_id, platform, context)
            
            # Get model name
            model = Config.AI_MODEL if Config.AI_MODEL != 'llama3.2' else Config.OPENAI_MODEL
            
            # Generate response
            logger.info(f"Generating OpenAI response with model {model}")
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=Config.AI_TEMPERATURE,
                max_tokens=Config.AI_MAX_TOKENS,
                timeout=Config.REQUEST_TIMEOUT
            )
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                
                # Store conversation history if enabled
                if Config.ENABLE_CHAT_CONTEXT:
                    self._update_conversation_history(user_id, message_content, content)
                
                # Clean and validate response
                cleaned_response = self._clean_response(content)
                logger.info(f"Generated OpenAI response: {cleaned_response}")
                
                return cleaned_response
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating OpenAI response: {str(e)}\n{traceback.format_exc()}")
            return None
    
    def get_available_models(self) -> list:
        """Get list of available OpenAI models"""
        try:
            if not self.client:
                self.initialize_client()
                
            models_response = self.client.models.list()
            # Filter for chat models
            chat_models = [model.id for model in models_response.data 
                          if 'gpt' in model.id.lower() or 'chat' in model.id.lower()]
            return sorted(chat_models)
        except Exception as e:
            logger.error(f"Failed to get available OpenAI models: {str(e)}")
            return ['gpt-3.5-turbo', 'gpt-4', 'gpt-4-turbo']  # Common fallback models
    
    def _build_messages(self, message_content: str, message_type: str, 
                       user_id: str, platform: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build messages array for OpenAI Chat API"""
        
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
        
        return messages
    
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