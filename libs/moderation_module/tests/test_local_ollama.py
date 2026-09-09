"""Unit tests for `LocalOllamaClassifier` -- mocked Ollama HTTP, no network."""

from __future__ import annotations

import httpx

from moderation_module.base import Classification
from moderation_module.providers.local_ollama import (
    ALTERNATE_MODEL,
    BASIC_CATEGORY_POLICIES,
    DEFAULT_MODEL,
    LocalOllamaClassifier,
    OllamaConfig,
)
from tests.conftest import ollama_logprobs_response


def _category_from_prompt(prompt: str) -> str | None:
    """Reverse-lookup which `BASIC_CATEGORY_POLICIES` entry a rendered prompt was built from."""
    for category, (policy_name, _desc) in BASIC_CATEGORY_POLICIES.items():
        if f'"{policy_name}"' in prompt:
            return category
    return None


def _client(handler, config: OllamaConfig | None = None) -> tuple[LocalOllamaClassifier, list]:  # noqa: ANN001
    """Build a classifier wired to a `MockTransport`; returns `(classifier, captured_requests)`."""
    captured: list = []

    def _wrapped(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return handler(request)

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(_wrapped))
    cfg = config or OllamaConfig(ollama_url="http://ollama.test:11434")
    return LocalOllamaClassifier(cfg, http_client=http_client), captured


# --- prompt construction -------------------------------------------------


class TestPromptConstruction:
    async def test_prompt_carries_message_and_policy_per_category(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            import json

            payload = json.loads(request.content)
            prompt = payload["prompt"]
            category = _category_from_prompt(prompt)
            assert category is not None, prompt
            policy_name, policy_description = BASIC_CATEGORY_POLICIES[category]
            assert policy_description in prompt
            assert "you filthy immigrant" in prompt
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-0.1, no_logprob=-3.0)
            )

        classifier, captured = _client(handler)
        result = await classifier.classify(
            "you filthy immigrant",
            {"hate_speech", "basic_harassment", "slurs"},
            tenant_id=1,
            community_id=1,
        )
        assert len(captured) == 3
        assert result is not None

    async def test_request_targets_configured_model(self) -> None:
        import json

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert payload["model"] == ALTERNATE_MODEL
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-5.0, no_logprob=-0.01)
            )

        cfg = OllamaConfig(ollama_url="http://ollama.test:11434", model=ALTERNATE_MODEL)
        classifier, captured = _client(handler, cfg)
        await classifier.classify("hi", {"hate_speech"}, tenant_id=1, community_id=1)
        assert len(captured) == 1

    async def test_request_uses_raw_mode_and_requests_logprobs(self) -> None:
        import json

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert payload["raw"] is True
            assert payload["logprobs"] is True
            assert payload["options"]["num_predict"] == 1
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-5.0, no_logprob=-0.01)
            )

        classifier, _ = _client(handler)
        await classifier.classify("hi", {"hate_speech"}, tenant_id=1, community_id=1)

    async def test_default_model_is_shieldgemma(self) -> None:
        assert DEFAULT_MODEL == "shieldgemma:2b"


# --- response parsing -----------------------------------------------------


class TestResponseParsing:
    async def test_high_confidence_yes_yields_high_severity_match(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-0.01, no_logprob=-6.0)
            )

        classifier, _ = _client(handler)
        result = await classifier.classify(
            "vile message", {"hate_speech"}, tenant_id=1, community_id=1
        )
        assert isinstance(result, Classification)
        assert result.category == "hate_speech"
        assert result.confidence > 0.9
        assert result.severity == "high"

    async def test_borderline_confidence_yields_medium_or_low_severity(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            # roughly P(yes) ~= 0.6 -- above match threshold, below "high"
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-0.5, no_logprob=-0.9)
            )

        classifier, _ = _client(handler)
        result = await classifier.classify("meh", {"hate_speech"}, tenant_id=1, community_id=1)
        assert result is not None
        assert result.severity in ("low", "medium")

    async def test_mid_range_confidence_yields_medium_severity(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            # P(yes) ~= 0.668 -- inside [0.65, 0.85), the "medium" bucket.
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-0.2, no_logprob=-0.9)
            )

        classifier, _ = _client(handler)
        result = await classifier.classify("meh", {"hate_speech"}, tenant_id=1, community_id=1)
        assert result is not None
        assert result.severity == "medium"

    async def test_missing_logprobs_field_degrades_to_zero_confidence(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"model": "shieldgemma:2b", "response": "No"})

        classifier, _ = _client(handler)
        result = await classifier.classify("hi", {"hate_speech"}, tenant_id=1, community_id=1)
        assert result is None


# --- enabled_categories filtering ------------------------------------------


class TestEnabledCategoriesFiltering:
    async def test_only_enabled_categories_trigger_calls(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-6.0, no_logprob=-0.01)
            )

        classifier, captured = _client(handler)
        await classifier.classify("hi", {"hate_speech"}, tenant_id=1, community_id=1)
        assert len(captured) == 1

    async def test_categories_outside_basic_set_are_skipped_no_call(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("should not be called for out-of-scope categories")

        classifier, captured = _client(handler)
        result = await classifier.classify(
            "hi", {"targeted_harassment", "prompt_injection"}, tenant_id=1, community_id=1
        )
        assert result is None
        assert captured == []

    async def test_mixed_enabled_categories_only_checks_basic_subset(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-6.0, no_logprob=-0.01)
            )

        classifier, captured = _client(handler)
        await classifier.classify(
            "hi", {"hate_speech", "doxxing_risk"}, tenant_id=1, community_id=1
        )
        assert len(captured) == 1

    async def test_empty_enabled_categories_makes_no_calls(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise AssertionError("should not be called")

        classifier, captured = _client(handler)
        result = await classifier.classify("hi", set(), tenant_id=1, community_id=1)
        assert result is None
        assert captured == []


# --- no-match / threshold ---------------------------------------------------


class TestNoMatch:
    async def test_all_below_threshold_returns_none(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-6.0, no_logprob=-0.01)
            )

        classifier, _ = _client(handler)
        result = await classifier.classify(
            "totally benign",
            {"hate_speech", "basic_harassment", "slurs"},
            tenant_id=1,
            community_id=1,
        )
        assert result is None

    async def test_custom_match_threshold_is_honored(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            # P(yes) ~= 0.6
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-0.5, no_logprob=-0.9)
            )

        strict_cfg = OllamaConfig(ollama_url="http://ollama.test:11434", match_threshold=0.9)
        classifier, _ = _client(handler, strict_cfg)
        result = await classifier.classify("hi", {"hate_speech"}, tenant_id=1, community_id=1)
        assert result is None

    async def test_best_of_multiple_matches_is_returned(self) -> None:
        import json

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            category = _category_from_prompt(payload["prompt"])
            if category == "slurs":
                return httpx.Response(
                    200, json=ollama_logprobs_response(yes_logprob=-0.01, no_logprob=-8.0)
                )
            return httpx.Response(
                200, json=ollama_logprobs_response(yes_logprob=-2.0, no_logprob=-0.3)
            )

        classifier, _ = _client(handler)
        result = await classifier.classify(
            "slur-laden message",
            {"hate_speech", "basic_harassment", "slurs"},
            tenant_id=1,
            community_id=1,
        )
        assert result is not None
        assert result.category == "slurs"

    async def test_unreachable_ollama_degrades_to_no_match(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        classifier, _ = _client(handler)
        result = await classifier.classify("hi", {"hate_speech"}, tenant_id=1, community_id=1)
        assert result is None


class TestClientLifecycle:
    """Constructor-injected vs. self-managed `httpx.AsyncClient` (`_client_or_new`)."""

    async def test_no_injected_client_builds_and_owns_one(self) -> None:
        classifier = LocalOllamaClassifier(OllamaConfig(ollama_url="http://ollama.test:11434"))
        client, owns_client = await classifier._client_or_new()
        try:
            assert owns_client is True
            assert isinstance(client, httpx.AsyncClient)
        finally:
            await client.aclose()

    async def test_injected_client_is_reused_not_owned(self) -> None:
        injected = httpx.AsyncClient()
        try:
            classifier = LocalOllamaClassifier(
                OllamaConfig(ollama_url="http://ollama.test:11434"), http_client=injected
            )
            client, owns_client = await classifier._client_or_new()
            assert owns_client is False
            assert client is injected
        finally:
            await injected.aclose()
