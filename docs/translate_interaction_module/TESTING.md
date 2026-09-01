# Translate Interaction Module — Testing

## Running Unit Tests

```bash
cd action/interactive/translate_interaction_module
pip install -r requirements.txt pytest pytest-asyncio
pytest tests/ -v
```

## Test Files

| File | Coverage |
|------|---------|
| `tests/test_translation_service.py` | TranslationService: detection, translation, skips, caching |
| `tests/test_ensemble_detector.py` | EnsembleDetector: per-language accuracy, confidence |
| `tests/test_translation_edge_cases.py` | Edge cases: empty text, Unicode, emote-only messages |
| `tests/test_translation_languages.py` | Multi-language translation accuracy |

## REST Smoke Test

```bash
# Start the module (requires DB + deps)
DATABASE_URL="postgresql://waddlebot:PASSWORD@localhost:5432/waddlebot" \
MODULE_SECRET_KEY="your_key_here" \
python app.py &

# Health check
curl -s http://localhost:8033/health | python3 -m json.tool

# Language detection
curl -s -X POST http://localhost:8033/api/v1/translate/detect \
  -H "Content-Type: application/json" \
  -d '{"text": "Hola, ¿cómo estás?"}' | python3 -m json.tool
# Expected: {"detected_lang": "es", "confidence": 0.99}

# Translate (requires community in DB with translation enabled)
curl -s -X POST http://localhost:8033/api/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Bonjour", "target_lang": "en", "community_id": "YOUR_COMMUNITY_ID"}' \
  | python3 -m json.tool
```

## gRPC Smoke Test (Python)

```python
# pip install grpcio grpcio-tools pyjwt
import asyncio, grpc, jwt, time, sys
sys.path.insert(0, 'action/interactive/translate_interaction_module')
from proto_clients import translate_interaction_pb2, translate_interaction_pb2_grpc

async def test():
    channel = grpc.aio.insecure_channel('localhost:50033')
    stub = translate_interaction_pb2_grpc.TranslateInteractionStub(channel)
    token = jwt.encode({'exp': int(time.time())+60}, 'your_secret', algorithm='HS256')
    resp = await stub.DetectLanguage(
        translate_interaction_pb2.DetectLanguageRequest(text="Bonjour", token=token)
    )
    print(resp)

asyncio.run(test())
```

## K8s Validation

```bash
kubectl kustomize k8s/kustomize/base/ | grep -A 15 "name: interactive-translate"
```
