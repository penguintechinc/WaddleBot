import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import traceback

from config import Config

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the AI provider is available"""
        pass
    
    @abstractmethod
    def generate_response(self, message_content: str, message_type: str, 
                         user_id: str, platform: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI response"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> list:
        """Get list of available models"""
        pass


class AIService:
    """Unified AI service that supports multiple providers"""
    
    def __init__(self):
        self.provider = None
        self.initialize_provider()
    
    def initialize_provider(self):
        """Initialize the AI provider based on configuration"""
        try:
            provider_type = Config.AI_PROVIDER.lower()
            
            if provider_type == 'ollama':
                from .ollama_provider import OllamaProvider
                self.provider = OllamaProvider()
            elif provider_type == 'openai':
                from .openai_provider import OpenAIProvider
                self.provider = OpenAIProvider()
            elif provider_type == 'mcp':
                from .mcp_provider import MCPProvider
                self.provider = MCPProvider()
            else:
                raise ValueError(f"Unsupported AI provider: {provider_type}")
            
            logger.info(f"Initialized {provider_type} AI provider")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI provider: {str(e)}")
            # Fallback to Ollama if available
            try:
                from .ollama_provider import OllamaProvider
                self.provider = OllamaProvider()
                logger.info("Fallback to Ollama provider")
            except Exception as fallback_error:
                logger.error(f"Fallback initialization failed: {str(fallback_error)}")
                raise
    
    def health_check(self) -> bool:
        """Check if the AI provider is available"""
        if not self.provider:
            return False
        return self.provider.health_check()
    
    def generate_response(self, message_content: str, message_type: str, 
                         user_id: str, platform: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI response using the configured provider"""
        if not self.provider:
            logger.error("No AI provider initialized")
            return self._get_fallback_response(message_type, context)
        
        try:
            return self.provider.generate_response(
                message_content, message_type, user_id, platform, context
            )
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}\n{traceback.format_exc()}")
            return self._get_fallback_response(message_type, context)
    
    def get_available_models(self) -> list:
        """Get list of available models from the provider"""
        if not self.provider:
            return []
        
        try:
            return self.provider.get_available_models()
        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return []
    
    def update_model(self, model_name: str):
        """Update the AI model"""
        try:
            Config.AI_MODEL = model_name
            # Reinitialize provider with new model
            self.initialize_provider()
            logger.info(f"Updated AI model to {model_name}")
        except Exception as e:
            logger.error(f"Failed to update model to {model_name}: {str(e)}")
            raise
    
    def _get_fallback_response(self, message_type: str, context: Dict[str, Any]) -> str:
        """Get fallback response when AI generation fails"""
        
        fallback_responses = {
            'chatMessage': "I'm having trouble processing that right now. Please try again!",
            'subscription': "Thanks for subscribing! 🎉",
            'follow': "Welcome to the community! 👋",
            'donation': "Thank you so much for your generosity! 💖",
            'cheer': "Thanks for the bits! 🎊",
            'raid': "Welcome raiders! 🚀",
            'boost': "Thanks for boosting! ⭐",
            'member_join': "Welcome! 👋"
        }
        
        return fallback_responses.get(message_type, "Thanks for interacting! 😊")