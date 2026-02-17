# Translate Interaction Module — Architecture

## Dual-Server Design

```
                    ┌─────────────────────────────────────┐
                    │   translate_interaction_module        │
                    │                                       │
  router_module ───►│  gRPC :50033  ──► TranslationService │
  (hot path)        │                        │             │
                    │  REST  :8033  ──► REST handlers       │
  admin/browser ───►│  (health/cache/detect)  │             │
                    └─────────────────────────┼─────────────┘
                                              │
                                   ┌──────────▼──────────┐
                                   │   3-Tier Cache       │
                                   │  1. In-memory LRU    │
                                   │  2. Redis            │
                                   │  3. PostgreSQL       │
                                   └─────────────────────┘
```

## Translation Pipeline

```
Input text
    │
    ▼
TranslationPreprocessor.preprocess()
    │  - Detect @mentions, !commands, URLs, emails → placeholders
    │  - Detect platform emotes (BTTV, 7TV, FFZ, native, Discord, Slack)
    │  - AI-assisted uncertain token decision (optional)
    │
    ▼
EnsembleDetector.detect_language()
    │  - fasttext (primary, fast)
    │  - lingua (secondary, accurate)
    │  - langdetect (tertiary, fallback)
    │  - Weighted majority vote
    │
    ▼ (skip if: already target lang, < min_words, < confidence_threshold)
    │
    ▼
Provider fallback chain:
    1. GoogleCloudProvider   (if google_api_key configured)
    2. GoogleTransProvider   (always available, free)
    3. WaddleAIProvider      (LLM fallback, local Ollama)
    │
    ▼
TranslationPreprocessor.restore()
    │  - Replace [[EMOTE_N]] placeholders with original tokens
    │
    ▼
Result → Cache (memory + Redis + PostgreSQL)
    │
    ▼
TranslateResponse (gRPC) / JSON (REST)
```

## Token Preservation

The preprocessor detects and protects these token types:

| Type | Examples |
|------|---------|
| Mentions | `@username`, `#channel` |
| Commands | `!command`, `!so` |
| URLs | `https://...` |
| Emails | `user@host.com` |
| Twitch native emotes | `Kappa`, `PogChamp`, `KEKW` |
| BTTV / FFZ / 7TV emotes | Channel-specific lookups via EmoteService |
| Discord emotes | `<:name:id>`, `<a:name:id>` |
| Slack emotes | `:emoji_name:` |

Unknown ALL_CAPS tokens use an optional WaddleAI decision call to determine if they are emotes.

## Three-Tier Cache

| Tier | TTL | Capacity | Notes |
|------|-----|----------|-------|
| In-memory LRU | 1 hour | 1,000 entries | `cachetools.TTLCache` |
| Redis | 24 hours | Unlimited | Shared across replicas |
| PostgreSQL (`translation_cache`) | 7 days | Unlimited | Persistent |

Cache key: `sha256(text + target_lang + community_id)`
