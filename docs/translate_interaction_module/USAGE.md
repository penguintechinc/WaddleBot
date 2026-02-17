# Translate Interaction Module — Usage

## gRPC Usage (Router → Translate)

The router calls `Translate` for every message in the hot path.

### Generate a token and call Translate

```python
import grpc
import jwt
import time
from proto_clients import translate_interaction_pb2, translate_interaction_pb2_grpc

channel = grpc.aio.insecure_channel('interactive-translate:50033')
stub = translate_interaction_pb2_grpc.TranslateInteractionStub(channel)

token = jwt.encode(
    {'service': 'router', 'iat': int(time.time()), 'exp': int(time.time()) + 3600},
    'YOUR_MODULE_SECRET_KEY',
    algorithm='HS256',
)

resp = await stub.Translate(translate_interaction_pb2.TranslateRequest(
    text="Hola, ¿cómo estás? KEKW PogChamp",
    target_lang="en",
    community_id="123",
    platform="twitch",
    channel_id="my_channel",
    token=token,
))

if resp.success and not resp.skipped:
    print(resp.translated_text)  # "Hello, how are you? KEKW PogChamp"
    print(resp.detected_lang)    # "es"
    print(resp.provider)         # "googletrans"
```

### Detect language only

```python
resp = await stub.DetectLanguage(translate_interaction_pb2.DetectLanguageRequest(
    text="Bonjour le monde",
    token=token,
))
print(resp.detected_lang, resp.confidence)  # "fr", 0.99
```

## REST Usage (Admin / Cache Management)

### Health check

```bash
curl http://localhost:8033/health
```

```json
{"status": "healthy", "module": "translate_interaction_module",
 "version": "1.0.0", "rest_port": 8033, "grpc_port": 50033}
```

### REST translate (for non-router callers)

```bash
curl -X POST http://localhost:8033/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour", "target_lang": "en", "community_id": "123"}'
```

### Detect language

```bash
curl -X POST http://localhost:8033/api/v1/translate/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola mundo"}'
```

### Cache stats

```bash
curl http://localhost:8033/api/v1/translate/cache/stats
```

### Cache cleanup

```bash
curl -X POST http://localhost:8033/api/v1/translate/cache/cleanup
```
