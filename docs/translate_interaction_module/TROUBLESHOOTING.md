# Translate Interaction Module — Troubleshooting

## Provider unavailable / all providers fail

**Symptom:** Logs show `Translation failed: all providers exhausted`

**Causes & Fixes:**
1. `deep-translator` network issue → check pod egress, `ping translate.googleapis.com`
2. Google Cloud API key expired → update `google_api_key` in `community_translation_settings`
3. WaddleAI (Ollama) down → check `ollama` pod: `kubectl logs -n waddlebot deployment/ollama`

## Low confidence, message not translated

**Symptom:** `skipped=true`, `skip_reason="confidence too low"`

**Fix:** Lower `confidence_threshold` in `community_translation_settings` (default 0.7, try 0.5 for short messages).

## Emote false positives (emotes being translated)

**Symptom:** Translated text contains garbled emote names.

**Causes & Fixes:**
1. Channel emote cache stale → call `POST /api/v1/translate/cache/cleanup`
2. BTTV/7TV/FFZ credentials not set → set `TWITCH_CLIENT_ID`/`TWITCH_CLIENT_SECRET`
3. New emote not yet cached → emote cache TTL is 24h; restart pod to force refresh

## gRPC authentication failures

**Symptom:** Router logs `UNAUTHENTICATED: Token expired` or `Invalid token`

**Fix:** Ensure router's `SECRET_KEY` matches translate module's `MODULE_SECRET_KEY` in K8s secrets.

## High memory usage

**Symptom:** Pod OOMKilled with 1Gi limit

**Cause:** `fasttext-wheel` loads a ~100MB model into memory per worker.

**Fix:** Reduce `GRPC_MAX_WORKERS` or increase memory limit to 2Gi in the Deployment.

## DB connection pool exhausted

**Symptom:** `psycopg2.OperationalError: connection pool exhausted`

**Fix:** The default `pool_size=10` in `DAL()` init in `app.py` can be increased via a config variable, or scale down replicas and increase pool size.

## proto import errors at runtime

**Symptom:** `ModuleNotFoundError: No module named 'translate_interaction_pb2'`

**Cause:** The Dockerfile regenerates stubs at build time. If you run locally without Docker, generate stubs manually:

```bash
cd action/interactive/translate_interaction_module
python3 -m grpc_tools.protoc -I proto --python_out=proto --grpc_python_out=proto proto/translate_interaction.proto
```
