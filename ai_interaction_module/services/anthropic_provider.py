import logging
import anthropic
from typing import Optional, Dict, Any, List
import traceback

from config import Config
from .ai_service import AIProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider implementation"""
    
    def __init__(self):
        self.client = None
        self.conversation_history = {}  # Simple in-memory conversation storage
        self.initialize_client()
    
    def initialize_client(self):
        """Initialize the Anthropic client"""
        try:
            api_key = Config.AI_API_KEY or Config.ANTHROPIC_API_KEY
            if not api_key:
                raise ValueError("Anthropic API key is required but not provided")
            
            # Configure Anthropic client
            self.client = anthropic.Anthropic(
                api_key=api_key,
            )
            
            logger.info("Initialized Anthropic client")
        except Exception as e:
            logger.error(f"Failed to initialize Anthropic client: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """Check if Anthropic API is available"""
        try:
            if not self.client:
                self.initialize_client()
                
            # Try a simple message as health check
            response = self.client.messages.create(
                model=Config.ANTHROPIC_MODEL,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            return response is not None
        except Exception as e:
            logger.error(f"Anthropic health check failed: {str(e)}")
            return False
    
    def generate_response(self, message_content: str, message_type: str, 
                         user_id: str, platform: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI response using Anthropic Claude"""
        try:
            if not self.client:
                self.initialize_client()
            
            # Build messages for the conversation
            messages = self._build_messages(message_content, message_type, user_id, platform, context)
            
            # Get model name
            model = Config.AI_MODEL if Config.AI_MODEL.startswith('claude') else Config.ANTHROPIC_MODEL
            
            # Generate response
            logger.info(f"Generating Anthropic response with model {model}")
            response = self.client.messages.create(
                model=model,
                max_tokens=Config.AI_MAX_TOKENS,
                temperature=Config.AI_TEMPERATURE,
                system=Config.SYSTEM_PROMPT,
                messages=messages
            )
            
            if response.content and len(response.content) > 0:
                # Get text content from response
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content = block.text
                        break
                
                if content:
                    # Store conversation history if enabled
                    if Config.ENABLE_CHAT_CONTEXT:
                        self._update_conversation_history(user_id, message_content, content)
                    
                    # Clean and validate response
                    cleaned_response = self._clean_response(content)
                    logger.info(f"Generated Anthropic response: {cleaned_response}")
                    
                    return cleaned_response
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating Anthropic response: {str(e)}\n{traceback.format_exc()}")
            return None
    
    def get_available_models(self) -> list:
        """Get list of available Anthropic models"""
        # Anthropic doesn't provide a model list endpoint, so we return known models
        return [
            'claude-3-5-sonnet-20241022',
            'claude-3-5-haiku-20241022', 
            'claude-3-opus-20240229',
            'claude-3-sonnet-20240229',
            'claude-3-haiku-20240307'
        ]
    
    def _build_messages(self, message_content: str, message_type: str, 
                       user_id: str, platform: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build messages array for Anthropic Messages API"""
        
        messages = []
        
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