"""Real (never stubbed) HTTP clients for every model-routing tier.

Free/premium both talk to Ollama (different endpoint+model, `OllamaConfig`);
BYOK talks directly to the community's own OpenAI/Anthropic account via
plain `httpx` REST calls (no official SDK -- avoids a new pinned dependency,
per this PR's own instructions; both APIs are simple enough that the direct
REST shape is barely more code than wrapping an SDK client would be). Every
`generate()` makes a real outbound call when reachable/credentialed -- there
is no mocked/fake code path here, only real requests; unit tests mock the
transport layer (`httpx.MockTransport`, `tests/test_analytics_proxy.py`'s
own established pattern), never this module's own logic. An unreachable
Ollama host, a rejected BYOK key, or a non-2xx provider response raises
`services.ai_routing.errors.provider_error()` -- graceful degradation (tier
fallback) happens one layer up, in `router.py`, never inside a client.

BYOK API keys are received already-decrypted (by `config_service.py`) and
used ONLY as an outbound header value here -- never logged, never echoed
into any response or exception message (`httpx.HTTPStatusError.__str__`
includes the request URL but not headers, so the default exception message
is safe to relay via `provider_error()`).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from services.ai_routing.errors import invalid_byok_key, provider_error
from services.ai_routing.models import AIRequest, AIResponse, ByokProvider, Tier
from services.ai_routing.pii_redaction import redact_pii

_DEFAULT_TIMEOUT_SECONDS = 60.0
_ANTHROPIC_API_VERSION = "2023-06-01"


@dataclass(slots=True, frozen=True)
class OllamaConfig:
    """One Ollama endpoint + model -- free and premium tiers each get their own."""

    base_url: str
    model: str
    timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS


def free_ollama_config() -> OllamaConfig:
    """`OLLAMA_URL` + `AI_FREE_MODEL` -- the always-reachable floor tier (spec §1/§6)."""
    return OllamaConfig(
        base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
        model=os.environ.get("AI_FREE_MODEL", "llama3.1:1b"),
    )


def premium_ollama_config() -> OllamaConfig:
    """`OLLAMA_PREMIUM_URL` (falls back to `OLLAMA_URL`) + `AI_PREMIUM_MODEL`.

    The "beefy host" MoE endpoint (spec §6) -- a separate env var so it can
    point at a dedicated GPU node pool distinct from the ubiquitous free
    endpoint; defaults to the same host as free-local for environments
    (local/alpha) that don't run a separate beefy Ollama yet. Live calls
    against a real beefy host are deferred to a later phase (task scope);
    this client is fully real today against whatever `OLLAMA_PREMIUM_URL`
    points at.
    """
    return OllamaConfig(
        base_url=os.environ.get(
            "OLLAMA_PREMIUM_URL", os.environ.get("OLLAMA_URL", "http://localhost:11434")
        ),
        model=os.environ.get("AI_PREMIUM_MODEL", "gemma2:27b"),
    )


class OllamaClient:
    """Real Ollama `/api/generate` client -- shared by the free and premium tiers."""

    def __init__(self, config: OllamaConfig) -> None:
        """Bind this client to one Ollama endpoint/model pair."""
        self._config = config

    async def generate(self, request: AIRequest, *, tier: Tier) -> AIResponse:
        """Call Ollama's non-streaming generate endpoint; normalize its own token counts."""
        payload = {
            "model": self._config.model,
            "prompt": request.prompt,
            "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._config.base_url, timeout=self._config.timeout_seconds
            ) as client:
                response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise provider_error(f"Ollama ({tier}) request failed: {exc}") from exc

        data = response.json()
        return AIResponse(
            text=str(data.get("response", "")),
            provider="ollama",
            model=self._config.model,
            tier_used=tier,
            input_tokens=int(data.get("prompt_eval_count", 0) or 0),
            output_tokens=int(data.get("eval_count", 0) or 0),
        )


class OpenAIClient:
    """Real OpenAI Chat Completions client -- BYOK tier, community's own key."""

    BASE_URL = "https://api.openai.com/v1"

    def __init__(self, *, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS) -> None:
        """Stateless besides the timeout -- the API key is passed per-call, never stored."""
        self._timeout_seconds = timeout_seconds

    async def generate(self, api_key: str, request: AIRequest) -> AIResponse:
        """POST `/chat/completions`; normalize OpenAI's `usage.{prompt,completion}_tokens`.

        `request.prompt` is redacted (`pii_redaction.redact_pii`) before it
        leaves this process -- this call crosses to a third-party API
        (the community's own OpenAI account), unlike the self-hosted Ollama
        tiers.
        """
        model = request.model_hint or os.environ.get("AI_BYOK_OPENAI_MODEL", "gpt-4o-mini")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": redact_pii(request.prompt)}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.BASE_URL, timeout=self._timeout_seconds
            ) as client:
                response = await client.post(
                    "/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json=payload,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            # httpx's default str() omits request/response headers (never the api_key).
            raise provider_error(f"OpenAI request failed: {exc}") from exc

        data = response.json()
        choices = data.get("choices") or [{}]
        text = str((choices[0].get("message") or {}).get("content", ""))
        usage = data.get("usage") or {}
        return AIResponse(
            text=text,
            provider="openai",
            model=model,
            tier_used="byok",
            input_tokens=int(usage.get("prompt_tokens", 0) or 0),
            output_tokens=int(usage.get("completion_tokens", 0) or 0),
        )


class AnthropicClient:
    """Real Anthropic Messages API client -- BYOK tier, community's own key."""

    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self, *, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS) -> None:
        """Stateless besides the timeout -- the API key is passed per-call, never stored."""
        self._timeout_seconds = timeout_seconds

    async def generate(self, api_key: str, request: AIRequest) -> AIResponse:
        """POST `/messages`; normalize Anthropic's `usage.{input,output}_tokens`.

        `request.prompt` is redacted (`pii_redaction.redact_pii`) before it
        leaves this process -- see `OpenAIClient.generate`'s docstring for
        why this tier redacts and the free/premium Ollama tiers don't.
        """
        model = request.model_hint or os.environ.get(
            "AI_BYOK_ANTHROPIC_MODEL", "claude-3-5-haiku-20241022"
        )
        payload = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": redact_pii(request.prompt)}],
        }
        try:
            async with httpx.AsyncClient(
                base_url=self.BASE_URL, timeout=self._timeout_seconds
            ) as client:
                response = await client.post(
                    "/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": _ANTHROPIC_API_VERSION,
                        "content-type": "application/json",
                    },
                    json=payload,
                )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise provider_error(f"Anthropic request failed: {exc}") from exc

        data = response.json()
        content_blocks = data.get("content") or [{}]
        text = "".join(str(block.get("text", "")) for block in content_blocks)
        usage = data.get("usage") or {}
        return AIResponse(
            text=text,
            provider="anthropic",
            model=model,
            tier_used="byok",
            input_tokens=int(usage.get("input_tokens", 0) or 0),
            output_tokens=int(usage.get("output_tokens", 0) or 0),
        )


def byok_client_for(provider: ByokProvider) -> OpenAIClient | AnthropicClient:
    """Return the real client for `provider` -- the only branch point BYOK dispatch needs."""
    if provider == "openai":
        return OpenAIClient()
    return AnthropicClient()


async def validate_byok_key(
    provider: ByokProvider, api_key: str, *, timeout_seconds: float = 10.0
) -> None:
    """Real, cheap validation call against the provider's own `/models` endpoint (spec §3).

    Called by `config_service.set_byok_key()` before a new/rotated key is
    encrypted and committed -- never persist a key that doesn't work.
    Raises `errors.invalid_byok_key()` on a `401`/`403` (the provider
    rejected this specific key), `errors.provider_error()` on any other
    failure (network error, 5xx, unexpected response) -- both real,
    typed outcomes, never a silent pass.
    """
    if provider == "openai":
        url = f"{OpenAIClient.BASE_URL}/models"
        headers = {"Authorization": f"Bearer {api_key}"}
    else:
        url = f"{AnthropicClient.BASE_URL}/models"
        headers = {"x-api-key": api_key, "anthropic-version": _ANTHROPIC_API_VERSION}

    try:
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            response = await client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        raise provider_error(f"{provider} key validation request failed: {exc}") from exc

    if response.status_code in (401, 403):
        raise invalid_byok_key(f"{provider} rejected this API key")
    if response.is_error:
        raise provider_error(f"{provider} key validation returned HTTP {response.status_code}")
