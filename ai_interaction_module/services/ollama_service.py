import logging
import requests
import json
from typing import Optional, Dict, Any
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema import BaseMessage
import traceback

from config import Config

logger = logging.getLogger(__name__)

class OllamaService:
    """Service for interacting with Ollama using LangChain"""
    
    def __init__(self):
        self.llm = None
        self.memory = ConversationBufferWindowMemory(
            k=Config.CONTEXT_HISTORY_LIMIT,
            return_messages=True
        ) if Config.ENABLE_CHAT_CONTEXT else None
        self.initialize_llm()
        
    def initialize_llm(self):
        """Initialize the Ollama LLM with LangChain"""
        try:
            self.llm = OllamaLLM(
                base_url=Config.OLLAMA_HOST,
                model=Config.OLLAMA_MODEL,
                temperature=Config.OLLAMA_TEMPERATURE,
                num_predict=Config.OLLAMA_MAX_TOKENS,
                timeout=Config.REQUEST_TIMEOUT
            )
            logger.info(f"Initialized Ollama LLM with model {Config.OLLAMA_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Ollama LLM: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """Check if Ollama is available"""
        try:
            response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {str(e)}")
            return False
    
    def generate_response(self, message_content: str, message_type: str, 
                         user_id: str, platform: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate AI response using LangChain and Ollama"""
        try:
            if not self.llm:
                self.initialize_llm()
            
            # Create context-aware prompt based on message type
            if message_type == 'chatMessage':
                prompt = self._create_chat_prompt(message_content, user_id, platform, context)
            else:
                prompt = self._create_event_prompt(message_type, user_id, platform, context)
            
            # Generate response
            logger.info(f"Generating response for: {prompt}")
            response = self.llm.invoke(prompt)
            
            # Store in memory if enabled
            if self.memory:
                self.memory.save_context(
                    {"input": message_content},
                    {"output": response}
                )
            
            # Clean and validate response
            cleaned_response = self._clean_response(response)
            logger.info(f"Generated response: {cleaned_response}")
            
            return cleaned_response
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}\n{traceback.format_exc()}")
            return self._get_fallback_response(message_type, context)
    
    def _create_chat_prompt(self, message_content: str, user_id: str, 
                           platform: str, context: Dict[str, Any]) -> str:
        """Create prompt for chat messages"""
        
        base_prompt = f"""You are a helpful AI assistant for a chat bot on {platform}. 
You should provide concise, friendly, and helpful responses to user questions.
Keep responses under 200 characters when possible for chat readability.

User {user_id} asked: {message_content}

Please provide a helpful response:"""
        
        # Add context if available
        if self.memory and Config.ENABLE_CHAT_CONTEXT:
            try:
                # Get conversation history
                history = self.memory.load_memory_variables({})
                if history.get('history'):
                    context_prompt = "Previous conversation context:\n"
                    for msg in history['history'][-3:]:  # Last 3 messages
                        if hasattr(msg, 'content'):
                            context_prompt += f"- {msg.content}\n"
                    base_prompt = context_prompt + "\n" + base_prompt
            except Exception as e:
                logger.warning(f"Failed to load conversation context: {str(e)}")
        
        return base_prompt
    
    def _create_event_prompt(self, message_type: str, user_id: str, 
                            platform: str, context: Dict[str, Any]) -> str:
        """Create prompt for event responses"""
        
        event_responses = {
            'subscription': f"User {user_id} just subscribed! Generate a celebratory thank you message.",
            'follow': f"User {user_id} just followed! Generate a welcoming thank you message.",
            'donation': f"User {user_id} just made a donation! Generate a grateful thank you message.",
            'cheer': f"User {user_id} just sent bits/cheered! Generate an excited thank you message.",
            'raid': f"User {user_id} just raided the channel! Generate a welcoming message for the raiders.",
            'boost': f"User {user_id} just boosted the server! Generate a thank you message for the boost.",
            'member_join': f"User {user_id} just joined! Generate a welcoming message."
        }
        
        specific_prompt = event_responses.get(
            message_type, 
            f"User {user_id} triggered a {message_type} event! Generate an appropriate response."
        )
        
        return f"""You are a helpful AI assistant for a chat bot on {platform}.
Generate a short, enthusiastic response (under 150 characters) for this event:

{specific_prompt}

Response:"""
    
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
    
    def _get_fallback_response(self, message_type: str, context: Dict[str, Any]) -> str:
        """Get fallback response when AI generation fails"""
        
        fallback_responses = {
            'chatMessage': "I'm having trouble processing that right now. Please try again!",
            'subscription': "Thanks for subscribing! <‰",
            'follow': "Welcome to the community! =K",
            'donation': "Thank you so much for your generosity! =",
            'cheer': "Thanks for the bits! P",
            'raid': "Welcome raiders! <Š",
            'boost': "Thanks for boosting! =€",
            'member_join': "Welcome! <‰"
        }
        
        return fallback_responses.get(message_type, "Thanks for interacting! =
")
    
    def update_model(self, model_name: str):
        """Update the Ollama model"""
        try:
            Config.OLLAMA_MODEL = model_name
            self.initialize_llm()
            logger.info(f"Updated Ollama model to {model_name}")
        except Exception as e:
            logger.error(f"Failed to update model to {model_name}: {str(e)}")
            raise
    
    def get_available_models(self) -> list:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [model['name'] for model in data.get('models', [])]
            return []
        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return []