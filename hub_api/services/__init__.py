"""hub-api Bot-module service layer.

Async service functions the `bot` blueprint group (`blueprints/v1/bot.py`)
calls into -- pydal against existing tables (no schema change) and httpx
proxy calls to the same downstream services the Node controllers called
(`server-manager-service`, `ai-interaction`, local Ollama), per
docs/plans/2026-08-31-hubapi-node-to-quart-migration.md M5.
"""

from __future__ import annotations
