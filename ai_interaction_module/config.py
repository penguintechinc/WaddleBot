import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://waddlebot:waddlebot_password@localhost:5432/waddlebot')
    
    # Core API Configuration
    CORE_API_URL = os.getenv('CORE_API_URL', 'http://localhost:8000')
    ROUTER_API_URL = os.getenv('ROUTER_API_URL', 'http://localhost:8000/router')
    
    # AI Provider Configuration
    AI_PROVIDER = os.getenv('AI_PROVIDER', 'ollama')  # 'ollama', 'openai', or 'mcp'
    AI_HOST = os.getenv('AI_HOST', 'http://ollama:11434')
    AI_PORT = int(os.getenv('AI_PORT', '11434'))
    AI_API_KEY = os.getenv('AI_API_KEY', '')
    
    # Model Configuration
    AI_MODEL = os.getenv('AI_MODEL', 'llama3.2')
    AI_TEMPERATURE = float(os.getenv('AI_TEMPERATURE', '0.7'))
    AI_MAX_TOKENS = int(os.getenv('AI_MAX_TOKENS', '500'))
    
    # OpenAI Specific Configuration
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    
    # MCP Configuration
    MCP_SERVER_URL = os.getenv('MCP_SERVER_URL', 'http://mcp-server:8080')
    MCP_TIMEOUT = int(os.getenv('MCP_TIMEOUT', '30'))
    
    # System Prompt Configuration
    SYSTEM_PROMPT = os.getenv('SYSTEM_PROMPT', 'You are a helpful chatbot assistant. Provide friendly, concise, and helpful responses to users in chat.')
    
    # Question Detection Configuration
    QUESTION_TRIGGERS = os.getenv('QUESTION_TRIGGERS', '?').split(',')
    RESPONSE_PREFIX = os.getenv('RESPONSE_PREFIX', '> ')
    
    # Module Information
    MODULE_NAME = os.getenv('MODULE_NAME', 'ai_interaction')
    MODULE_VERSION = os.getenv('MODULE_VERSION', '1.0.0')
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '10'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    # Context Configuration
    ENABLE_CHAT_CONTEXT = os.getenv('ENABLE_CHAT_CONTEXT', 'true').lower() == 'true'
    CONTEXT_HISTORY_LIMIT = int(os.getenv('CONTEXT_HISTORY_LIMIT', '5'))
    
    # Event Response Configuration
    RESPOND_TO_EVENTS = os.getenv('RESPOND_TO_EVENTS', 'true').lower() == 'true'
    EVENT_RESPONSE_TYPES = os.getenv('EVENT_RESPONSE_TYPES', 'subscription,follow,donation').split(',')
    
    # Legacy Ollama Configuration (for backward compatibility)
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', AI_HOST)
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', AI_MODEL)
    OLLAMA_TEMPERATURE = AI_TEMPERATURE
    OLLAMA_MAX_TOKENS = AI_MAX_TOKENS