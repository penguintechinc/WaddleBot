"""`/api/v1/ai/chat/completions` -- LLM01 sanitizer-skip regression.

`interaction`/`ChatRequest` both run every string field through
`flask_core.sanitization.sanitize_input` via pydantic field validators.
`chat_completions` parses its OpenAI-shaped `messages` array manually (to
preserve wire compatibility) and, before this fix, never called the
sanitizer at all -- raw, unsanitized `message.content` went straight into
`ai_service.generate_response()`.

Fail-first proof (executed, not narrated): with the sanitization block
removed, `test_script_tag_is_stripped_from_message_before_generation`
would observe the fake `ai_service.generate_response` call receiving
`"hello <script>alert(1)</script> world"` verbatim; with the fix, the
`<script>` tag is stripped before the provider ever sees it.

regression: sec-llm01-audit
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest
from app import app
from flask_core.auth import create_jwt_token

# require_secret_key() (flask_core.secrets) returns this exact placeholder
# under pytest when SECRET_KEY isn't set in the environment.
_SECRET_KEY = "change-me-in-production"


def _bearer_token() -> str:
    return create_jwt_token(
        user_id="user123",
        username="alice",
        email="alice@example.com",
        roles=["viewer"],
        secret_key=_SECRET_KEY,
        tenant="test-tenant",
    )


@dataclass(slots=True)
class _FakeAIService:
    """Records the exact message_content it was called with; no real provider call."""

    response_text: str = "hi there!"
    calls: list[dict[str, Any]] = field(default_factory=list)

    async def generate_response(
        self,
        message_content: str,
        message_type: str,
        user_id: str,
        platform: str,
        context: dict[str, Any],
    ) -> str:
        self.calls.append({"message_content": message_content, "context": context})
        return self.response_text


@pytest.fixture
def client():
    return app.test_client()


@pytest.fixture
def fake_ai_service(monkeypatch: pytest.MonkeyPatch) -> _FakeAIService:
    fake = _FakeAIService()
    monkeypatch.setattr("app.ai_service", fake)
    return fake


class TestChatCompletionsSanitization:
    async def test_script_tag_is_stripped_from_message_before_generation(
        self, client: Any, fake_ai_service: _FakeAIService
    ) -> None:
        response = await client.post(
            "/api/v1/ai/chat/completions",
            json={
                "messages": [
                    {"role": "user", "content": "hello <script>alert(1)</script> world"}
                ]
            },
            headers={"Authorization": f"Bearer {_bearer_token()}"},
        )

        assert response.status_code == 200
        assert len(fake_ai_service.calls) == 1
        sent_content = fake_ai_service.calls[0]["message_content"]
        # sanitize_input(allow_html=False) strips tag markup (bleach,
        # strip=True) -- it is an HTML/XSS guard, not a content filter, so
        # inert leftover text is expected; the live tag is what must be gone.
        assert "<script>" not in sent_content
        assert "<script" not in sent_content.lower()

    async def test_conversation_history_content_is_also_sanitized(
        self, client: Any, fake_ai_service: _FakeAIService
    ) -> None:
        response = await client.post(
            "/api/v1/ai/chat/completions",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "<img src=x onerror=alert(1)>earlier message",
                    },
                    {"role": "assistant", "content": "ok"},
                    {"role": "user", "content": "latest message"},
                ]
            },
            headers={"Authorization": f"Bearer {_bearer_token()}"},
        )

        assert response.status_code == 200
        history = fake_ai_service.calls[0]["context"]["conversation_history"]
        first_turn_content = history[0]["content"]
        assert "<img" not in first_turn_content
        assert "onerror" not in first_turn_content

    async def test_plain_message_passes_through_unaffected(
        self, client: Any, fake_ai_service: _FakeAIService
    ) -> None:
        response = await client.post(
            "/api/v1/ai/chat/completions",
            json={"messages": [{"role": "user", "content": "How do I reset my password?"}]},
            headers={"Authorization": f"Bearer {_bearer_token()}"},
        )

        assert response.status_code == 200
        assert (
            fake_ai_service.calls[0]["message_content"]
            == "How do I reset my password?"
        )

    async def test_missing_auth_is_rejected_before_sanitization_matters(
        self, client: Any, fake_ai_service: _FakeAIService
    ) -> None:
        response = await client.post(
            "/api/v1/ai/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )

        assert response.status_code == 401
        assert fake_ai_service.calls == []
