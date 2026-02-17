# Translate Interaction Module — API Reference

## gRPC Service: TranslateInteraction (port 50033)

Defined in `proto/translate_interaction.proto`.

### Translate

Hot-path message translation, called by `router_module`.

**Request: TranslateRequest**

| Field | Type | Description |
|-------|------|-------------|
| text | string | Raw chat message |
| target_lang | string | BCP-47 language code (e.g. "en", "es") |
| community_id | string | Community identifier |
| platform | string | "twitch", "discord", "slack", "kick", "youtube" |
| channel_id | string | Channel ID for emote context lookups |
| token | string | JWT signed with MODULE_SECRET_KEY |

**Response: TranslateResponse**

| Field | Type | Description |
|-------|------|-------------|
| success | bool | Whether the call succeeded |
| skipped | bool | True if translation was not needed |
| skip_reason | string | Reason for skip (if skipped=true) |
| translated_text | string | Translated message with emotes restored |
| original_text | string | Original message text |
| detected_lang | string | Detected source language (BCP-47) |
| target_lang | string | Target language used |
| confidence | float | Detection confidence 0.0–1.0 |
| provider | string | Provider used: "google_cloud", "googletrans", "waddleai" |
| cached | bool | True if result was served from cache |
| tokens_preserved | int32 | Number of tokens (emotes/mentions) preserved |
| error | string | Error message (if success=false) |

### DetectLanguage

Detect language without translating.

**Request: DetectLanguageRequest** — `text`, `token`

**Response: DetectLanguageResponse** — `success`, `detected_lang`, `confidence`, `error`

### CleanupCache

Trigger expired cache entry cleanup.

**Request: CleanupCacheRequest** — `token`

**Response: CleanupCacheResponse** — `success`, `message`, `error`

---

## REST API (port 8033)

### GET /health

Returns service health and version info.

### POST /api/v1/translate

Body: `{"text": str, "target_lang": str, "community_id": str, "platform": str?, "channel_id": str?}`

Returns: `{"status": "success", "data": {...}}` or `{"skipped": true, "reason": "..."}`

### POST /api/v1/translate/detect

Body: `{"text": str}`

Returns: `{"detected_lang": str, "confidence": float}`

### GET /api/v1/translate/cache/stats

Returns cache hit/miss statistics from translation_service.

### POST /api/v1/translate/cache/cleanup

Triggers cleanup of expired entries from all cache tiers.
