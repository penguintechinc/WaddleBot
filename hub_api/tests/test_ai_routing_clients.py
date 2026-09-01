"""`services/ai_routing/clients.py` -- real HTTP-forwarding logic, transport mocked only.

`httpx.MockTransport` (real `httpx` request/response objects, no real socket)
-- same technique `tests/test_analytics_proxy.py` establishes for this repo.
Nothing about `OllamaClient`/`OpenAIClient`/`AnthropicClient`'s own request-
building or response-parsing logic is mocked; only the actual network call
is intercepted.
"""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from services.ai_routing.clients import (
    AnthropicClient,
    OllamaClient,
    OllamaConfig,
    OpenAIClient,
    validate_byok_key,
)
from services.ai_routing.errors import ApiError
from services.ai_routing.models import AIRequest


def _patch_transport(
    monkeypatch: pytest.MonkeyPatch, handler: Callable[[httpx.Request], httpx.Response]
) -> None:
    """Force every `httpx.AsyncClient` built inside `clients.py` onto a mock transport."""
    transport = httpx.MockTransport(handler)
    original_init = httpx.AsyncClient.__init__

    def patched_init(self: httpx.AsyncClient, *args: object, **kwargs: object) -> None:
        kwargs["transport"] = transport
        original_init(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx.AsyncClient, "__init__", patched_init)


class TestOllamaClient:
    async def test_generate_normalizes_usage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/generate"
            return httpx.Response(
                200, json={"response": "hello", "prompt_eval_count": 12, "eval_count": 8}
            )

        _patch_transport(monkeypatch, handler)
        client = OllamaClient(OllamaConfig(base_url="http://ollama.test", model="llama3.1:1b"))
        response = await client.generate(AIRequest(prompt="hi"), tier="free")

        assert response.text == "hello"
        assert response.provider == "ollama"
        assert response.model == "llama3.1:1b"
        assert response.tier_used == "free"
        assert response.input_tokens == 12
        assert response.output_tokens == 8
        assert response.total_tokens == 20

    async def test_generate_raises_provider_error_on_http_failure(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "model not found"})

        _patch_transport(monkeypatch, handler)
        client = OllamaClient(OllamaConfig(base_url="http://ollama.test", model="gemma2:27b"))
        with pytest.raises(ApiError) as exc_info:
            await client.generate(AIRequest(prompt="hi"), tier="premium")
        assert exc_info.value.status_code == 502
        assert exc_info.value.code == "AI_PROVIDER_ERROR"


class TestOpenAIClient:
    async def test_generate_normalizes_usage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/chat/completions"
            assert request.headers["authorization"] == "Bearer sk-test-key"
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": "hi there"}}],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 3},
                },
            )

        _patch_transport(monkeypatch, handler)
        client = OpenAIClient()
        response = await client.generate(
            "sk-test-key", AIRequest(prompt="hi", model_hint="gpt-4o-mini")
        )

        assert response.text == "hi there"
        assert response.provider == "openai"
        assert response.tier_used == "byok"
        assert response.input_tokens == 5
        assert response.output_tokens == 3

    async def test_generate_never_includes_key_in_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": {"message": "invalid api key"}})

        _patch_transport(monkeypatch, handler)
        client = OpenAIClient()
        with pytest.raises(ApiError) as exc_info:
            await client.generate("sk-super-secret-value", AIRequest(prompt="hi"))
        assert "sk-super-secret-value" not in exc_info.value.message


class TestAnthropicClient:
    async def test_generate_normalizes_usage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/v1/messages"
            assert request.headers["x-api-key"] == "anthropic-test-key"
            return httpx.Response(
                200,
                json={
                    "content": [{"type": "text", "text": "hi there"}],
                    "usage": {"input_tokens": 6, "output_tokens": 4},
                },
            )

        _patch_transport(monkeypatch, handler)
        client = AnthropicClient()
        response = await client.generate("anthropic-test-key", AIRequest(prompt="hi"))

        assert response.text == "hi there"
        assert response.provider == "anthropic"
        assert response.input_tokens == 6
        assert response.output_tokens == 4


class TestValidateByokKey:
    async def test_valid_openai_key_passes(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"data": []})

        _patch_transport(monkeypatch, handler)
        await validate_byok_key("openai", "sk-good")  # does not raise

    async def test_rejected_key_raises_invalid_byok_key(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"error": "invalid key"})

        _patch_transport(monkeypatch, handler)
        with pytest.raises(ApiError) as exc_info:
            await validate_byok_key("anthropic", "bad-key")
        assert exc_info.value.status_code == 400
        assert exc_info.value.code == "AI_BYOK_KEY_INVALID"

    async def test_provider_5xx_raises_provider_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        _patch_transport(monkeypatch, handler)
        with pytest.raises(ApiError) as exc_info:
            await validate_byok_key("openai", "sk-whatever")
        assert exc_info.value.status_code == 502
