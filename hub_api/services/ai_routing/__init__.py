"""Premium-AI model-routing layer -- free-local / premium-local-metered / BYOK.

See `docs/plans/2026-08-31-premium-ai-routing-design.md` for the design this
package implements. `router.route_completion()` is the single entrypoint
every AI-using caller in hub-api goes through; `config_service` owns
per-community tier choice + encrypted-at-rest BYOK keys; `clients` holds the
real (never stubbed) Ollama/OpenAI/Anthropic HTTP clients;
`services.token_ledger` (top-level, shared with the future transcoding
consumable) owns the premium-tier metering hook.
"""

from __future__ import annotations

from services.ai_routing.models import AIRequest, AIResponse
from services.ai_routing.router import route_completion

__all__ = ["AIRequest", "AIResponse", "route_completion"]
