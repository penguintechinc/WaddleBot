# WaddleBot AI Interaction Module API

The AI Interaction Module provides a REST API for other WaddleBot modules to access AI services through Kong API Gateway. It supports multiple AI providers (Ollama, OpenAI, MCP) with a unified interface.

## Base URL
All API endpoints are accessible through Kong API Gateway:
```
https://your-domain.com/api/ai/
```

## Authentication
All API endpoints require authentication via API key in the header:
```http
X-API-Key: your_api_key_here
```

API keys are managed through Kong and configured in the Kong consumers section.

## Endpoints

### 1. Chat Completions (OpenAI Compatible)

**Endpoint:** `POST /api/ai/v1/chat/completions`

OpenAI-compatible chat completions endpoint for seamless integration with existing tools.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful assistant."
    },
    {
      "role": "user", 
      "content": "Hello, how are you?"
    }
  ],
  "model": "llama3.2",
  "temperature": 0.7,
  "max_tokens": 500,
  "user": "user123"
}
```

**Response:**
```json
{
  "id": "chatcmpl-1234567890",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "llama3.2",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 12,
    "completion_tokens": 18,
    "total_tokens": 30
  },
  "metadata": {
    "provider": "ollama",
    "processing_time_ms": 850
  }
}
```

### 2. Simple Text Generation

**Endpoint:** `POST /api/ai/v1/generate`

Simple text generation endpoint for basic AI text completion.

**Request Body:**
```json
{
  "prompt": "Write a short poem about cats",
  "user_id": "user123",
  "platform": "discord",
  "model": "llama3.2",
  "temperature": 0.8,
  "max_tokens": 200
}
```

**Response:**
```json
{
  "success": true,
  "prompt": "Write a short poem about cats",
  "generated_text": "Whiskers twitching in the night,\nSilent paws on windowsill,\nEyes like emeralds burning bright,\nGraceful hunters, calm and still.",
  "metadata": {
    "provider": "ollama", 
    "model": "llama3.2",
    "processing_time_ms": 1200,
    "user_id": "user123",
    "platform": "discord"
  }
}
```

### 3. List Available Models

**Endpoint:** `GET /api/ai/v1/models`

List all available AI models from the current provider.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "llama3.2",
      "object": "model",
      "created": 1234567890,
      "owned_by": "ollama",
      "provider": "ollama"
    },
    {
      "id": "mistral",
      "object": "model", 
      "created": 1234567890,
      "owned_by": "ollama",
      "provider": "ollama"
    }
  ],
  "current_model": "llama3.2",
  "current_provider": "ollama"
}
```

### 4. Health Check

**Endpoint:** `GET /api/ai/v1/health`

Check the health status of the AI service. **No authentication required.**

**Response:**
```json
{
  "status": "healthy",
  "provider": "ollama",
  "model": "llama3.2", 
  "ai_service": "connected",
  "timestamp": 1234567890
}
```

### 5. Get Configuration

**Endpoint:** `GET /api/ai/v1/config`

Get current AI service configuration.

**Response:**
```json
{
  "provider": "ollama",
  "model": "llama3.2",
  "temperature": 0.7,
  "max_tokens": 500,
  "system_prompt": "You are a helpful chatbot assistant...",
  "question_triggers": ["?"],
  "response_prefix": "🤖 ",
  "context_enabled": true,
  "context_limit": 5,
  "event_responses": true,
  "event_types": ["subscription", "follow", "donation"]
}
```

### 6. Update Configuration

**Endpoint:** `PUT /api/ai/v1/config`

Update AI service configuration dynamically.

**Request Body:**
```json
{
  "provider": "openai",
  "model": "gpt-4",
  "temperature": 0.8,
  "max_tokens": 1000,
  "system_prompt": "You are a creative writing assistant."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Updated configuration fields: provider, model, temperature, max_tokens, system_prompt",
  "updated_fields": ["provider", "model", "temperature", "max_tokens", "system_prompt"],
  "current_config": {
    "provider": "openai",
    "model": "gpt-4", 
    "temperature": 0.8,
    "max_tokens": 1000
  }
}
```

### 7. List AI Providers

**Endpoint:** `GET /api/ai/v1/providers`

List all available AI providers and their status.

**Response:**
```json
{
  "providers": {
    "ollama": {
      "name": "Ollama",
      "description": "Local LLM hosting with LangChain integration",
      "status": "available",
      "health": "healthy",
      "current": true,
      "config_required": ["AI_HOST", "AI_MODEL"]
    },
    "openai": {
      "name": "OpenAI",
      "description": "OpenAI API integration", 
      "status": "available",
      "config_required": ["OPENAI_API_KEY", "OPENAI_MODEL"]
    },
    "mcp": {
      "name": "Model Context Protocol",
      "description": "Standardized AI model communication protocol",
      "status": "available", 
      "config_required": ["MCP_SERVER_URL", "AI_MODEL"]
    }
  },
  "current_provider": "ollama"
}
```

## Kong Integration

### Routes Configuration
The AI module is integrated with Kong using the following routes:

- **API Routes:** `/api/ai/*` → `ai-interaction:8005` (with authentication)
- **Web UI:** `/ai/*` → `ai-interaction:8005` (no auth for health endpoints)
- **Health Check:** `/ai/health` → `ai-interaction:8005` (no authentication)

### Authentication
Kong handles API key authentication using the `key-auth` plugin. API keys are configured for different consumer types:

- `ai-interaction-service` - Service-to-service communication
- `ai-api-user` - General API access

### Rate Limiting
Kong applies rate limiting to AI endpoints:
- **1000 requests per minute**
- **10000 requests per hour**

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": {
    "code": 400,
    "message": "Invalid request format",
    "type": "validation_error"
  }
}
```

Common HTTP status codes:
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid API key)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error (AI service failure)
- `503` - Service Unavailable (AI provider offline)

## Usage Examples

### Using curl

```bash
# Chat completion request
curl -X POST https://your-domain.com/api/ai/v1/chat/completions \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "model": "llama3.2"
  }'

# Simple text generation
curl -X POST https://your-domain.com/api/ai/v1/generate \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing",
    "max_tokens": 200
  }'

# Health check (no auth required)
curl https://your-domain.com/ai/health
```

### Using Python

```python
import requests

# Configure API
API_BASE = "https://your-domain.com/api/ai"
API_KEY = "your_api_key"
headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

# Chat completion
response = requests.post(
    f"{API_BASE}/v1/chat/completions",
    headers=headers,
    json={
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "model": "llama3.2"
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

### Using JavaScript/Node.js

```javascript
const axios = require('axios');

const apiClient = axios.create({
  baseURL: 'https://your-domain.com/api/ai',
  headers: {
    'X-API-Key': 'your_api_key',
    'Content-Type': 'application/json'
  }
});

// Chat completion
async function chatComplete(message) {
  try {
    const response = await apiClient.post('/v1/chat/completions', {
      messages: [
        { role: 'user', content: message }
      ],
      model: 'llama3.2'
    });
    
    return response.data.choices[0].message.content;
  } catch (error) {
    console.error('API Error:', error.response?.data || error.message);
  }
}

// Usage
chatComplete("Hello, how are you?").then(console.log);
```

## Provider-Specific Notes

### Ollama Provider
- Requires local Ollama installation
- Models must be pulled locally: `ollama pull llama3.2`
- Supports GPU acceleration if available
- Best for privacy and local deployment

### OpenAI Provider  
- Requires OpenAI API key
- Supports all OpenAI chat models (gpt-3.5-turbo, gpt-4, etc.)
- Pay-per-use pricing
- Best for production and advanced capabilities

### MCP Provider
- Requires MCP-compatible server
- Standardized protocol for AI model communication
- Good for custom AI deployments
- Experimental support

## Environment Configuration

Configure the AI module using environment variables:

```bash
# Provider Selection
AI_PROVIDER=ollama          # 'ollama', 'openai', or 'mcp'
AI_HOST=http://ollama:11434
AI_API_KEY=your_api_key

# Model Configuration
AI_MODEL=llama3.2
AI_TEMPERATURE=0.7
AI_MAX_TOKENS=500

# System Behavior
SYSTEM_PROMPT="You are a helpful assistant"
QUESTION_TRIGGERS=?
RESPONSE_PREFIX="🤖 "
```

For more configuration options, see the main WaddleBot documentation.