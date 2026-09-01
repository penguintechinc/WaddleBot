# AI Interaction Module - Usage Guide

## Quick Start

### 1. Installation

```bash
cd /home/penguin/code/WaddleBot/action/interactive/ai_interaction_module
pip install -r requirements.txt
```

### 2. Configuration

Create `.env` file:

```env
AI_PROVIDER=waddleai
WADDLEAI_BASE_URL=http://waddleai-proxy:8000
WADDLEAI_API_KEY=wa-your-api-key-here
MODULE_PORT=8005
DATABASE_URL=postgresql://waddlebot:password@localhost:5432/waddlebot
```

### 3. Start Module

```bash
python app.py
```

Expected output:
```
[SYSTEM] Starting AI interaction module
[SYSTEM] Initialized AI service with provider: waddleai
[SYSTEM] AI provider health check passed
INFO: Running on http://0.0.0.0:8005
```

---

## Basic Usage

### Send Chat Message

```bash
curl -X POST http://localhost:8005/api/v1/ai/interaction \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess_123",
    "message_type": "chatMessage",
    "message_content": "Hello, how are you?",
    "user_id": "user_456",
    "entity_id": "twitch:channel:789",
    "platform": "twitch",
    "username": "testuser"
  }'
```

### Test AI Response

```bash
curl -X POST http://localhost:8005/api/v1/ai/test \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message": "Tell me a joke"}'
```

### Check Health

```bash
curl http://localhost:8005/health
```

---

## Common Use Cases

### 1. Greeting Detection

The module automatically responds to greetings:

**Triggers:** o7, hi, hello, hey, howdy, greetings, sup, hiya

**Example:**
```
User: "o7 everyone!"
Bot: "🤖 Hey there! Welcome to the stream!"
```

### 2. Question Answering

Responds to messages containing question triggers:

**Default Trigger:** `?`

**Example:**
```
User: "What game are we playing?"
Bot: "🤖 We're currently playing Elden Ring! Check the game info below."
```

### 3. Event Responses

Responds to platform events (if enabled):

**Supported Events:**
- subscription
- follow
- donation
- cheer
- raid
- boost

**Example:**
```
Event: New subscription from JohnDoe
Bot: "🤖 Thank you JohnDoe for subscribing! Welcome to the community!"
```

### 4. Farewell Messages

Responds to farewell patterns:

**Triggers:** !lurk, bye, goodbye, later, cya

**Example:**
```
User: "!lurk gotta go, thanks for the stream!"
Bot: "🤖 Thanks for hanging out! See you next time!"
```

---

## Advanced Usage

### OpenAI-Compatible Chat

```python
import requests

response = requests.post(
    "http://localhost:8005/api/v1/ai/chat/completions",
    headers={"Authorization": "Bearer your-api-key"},
    json={
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "model": "auto",
        "temperature": 0.7,
        "max_tokens": 500
    }
)

result = response.json()
print(result['data']['choices'][0]['message']['content'])
```

### Custom Configuration

```bash
curl -X PUT http://localhost:8005/api/v1/ai/config \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "community_id": 123,
    "model": "gpt-4",
    "temperature": 0.8,
    "system_prompt": "You are Waddles, a friendly penguin assistant for streamers."
  }'
```

### List Available Models

```bash
curl http://localhost:8005/api/v1/ai/models
```

---

## Integration Examples

### Python Integration

```python
import asyncio
import httpx

class AIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def send_message(self, message: str, user_id: str, community_id: str):
        response = await self.client.post(
            f"{self.base_url}/api/v1/ai/interaction",
            json={
                "session_id": f"sess_{user_id}",
                "message_type": "chatMessage",
                "message_content": message,
                "user_id": user_id,
                "entity_id": f"community:{community_id}",
                "platform": "api",
                "username": user_id
            }
        )
        return response.json()

# Usage
client = AIClient("http://localhost:8005")
result = await client.send_message("Hello!", "user123", "comm456")
```

### JavaScript Integration

```javascript
class AIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async chatCompletion(messages, apiKey) {
    const response = await fetch(`${this.baseUrl}/api/v1/ai/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        messages: messages,
        model: 'auto',
        temperature: 0.7
      })
    });

    const data = await response.json();
    return data.data.choices[0].message.content;
  }
}

// Usage
const client = new AIClient('http://localhost:8005');
const response = await client.chatCompletion([
  {role: 'user', content: 'Hello!'}
], 'your-api-key');
```

---

## Troubleshooting

### Issue: Module won't start

**Check:**
1. Port 8005 is available
2. Database connection is valid
3. Environment variables are set

```bash
# Test database connection
psql postgresql://waddlebot:password@localhost:5432/waddlebot -c "SELECT 1"

# Check port
netstat -tulpn | grep 8005
```

### Issue: AI responses are slow

**Solutions:**
1. Increase timeout: `REQUEST_TIMEOUT=60`
2. Check provider latency
3. Reduce max_tokens: `AI_MAX_TOKENS=300`
4. Enable caching

### Issue: Provider errors

**Ollama:**
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags
```

**WaddleAI:**
```bash
# Test API key
curl http://waddleai-proxy:8000/health \
  -H "Authorization: Bearer wa-your-key"
```

### Issue: No responses to messages

**Check trigger patterns:**
```python
# Does message match any trigger?
message = "user message here"
triggers = ['?']  # Check QUESTION_TRIGGERS

if any(t in message for t in triggers):
    print("Should trigger response")
```

---

## Best Practices

1. **Use Appropriate Timeouts**: Set based on provider (Ollama: 30s, WaddleAI: 45s)
2. **Enable Context for Better Responses**: Set `ENABLE_CHAT_CONTEXT=true`
3. **Monitor Response Times**: Track p95 latency
4. **Set Reasonable Token Limits**: 200-500 for chat, 1000+ for detailed responses
5. **Test with Various Inputs**: Greetings, questions, commands
6. **Use Health Checks**: Monitor `/health` endpoint
7. **Configure Response Prefix**: Help users identify bot messages
8. **Limit Concurrent Requests**: Prevent provider overload

---

## Performance Tips

1. **Reduce Token Count**: Lower tokens = faster responses
2. **Use Caching**: Enable conversation context caching
3. **Optimize System Prompt**: Keep it concise
4. **Monitor Provider Health**: Use circuit breaker pattern
5. **Load Balance**: Deploy multiple instances
6. **Use WaddleAI**: Better reliability than direct Ollama

---

## Common Commands

```bash
# Start module
python app.py

# Start with custom port
MODULE_PORT=9000 python app.py

# Enable debug logging
LOG_LEVEL=DEBUG python app.py

# Test with curl
curl http://localhost:8005/health

# View logs
tail -f /var/log/waddlebotlog/ai_interaction_module.log
```
