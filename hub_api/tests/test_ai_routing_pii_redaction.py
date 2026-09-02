"""`services/ai_routing/pii_redaction.py` -- redaction applied before BYOK egress."""

from __future__ import annotations

from services.ai_routing.pii_redaction import redact_pii


class TestRedactPii:
    def test_email_is_redacted(self) -> None:
        result = redact_pii("Contact me at jane.doe@example.com about the issue")
        assert "jane.doe@example.com" not in result
        assert "[REDACTED_EMAIL]" in result

    def test_multiple_emails_all_redacted(self) -> None:
        result = redact_pii("cc alice@example.com and bob@example.org please")
        assert "alice@example.com" not in result
        assert "bob@example.org" not in result
        assert result.count("[REDACTED_EMAIL]") == 2

    def test_openai_style_key_is_redacted(self) -> None:
        result = redact_pii("my key is sk-abcdefghijklmnopqrstuvwxyz123456")
        assert "sk-abcdefghijklmnopqrstuvwxyz123456" not in result
        assert "[REDACTED_TOKEN]" in result

    def test_waddleai_style_key_is_redacted(self) -> None:
        result = redact_pii("here's my token wa-1234567890abcdefghij for testing")
        assert "wa-1234567890abcdefghij" not in result
        assert "[REDACTED_TOKEN]" in result

    def test_bearer_header_is_redacted(self) -> None:
        result = redact_pii("send with header Authorization: Bearer abc123def456ghi789")
        assert "abc123def456ghi789" not in result
        assert "[REDACTED_TOKEN]" in result

    def test_jwt_is_redacted(self) -> None:
        # Synthetic test fixture, not a real credential -- gitleaks:allow
        jwt = (
            "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."  # gitleaks:allow
            "dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"  # gitleaks:allow
        )
        result = redact_pii(f"my session token is {jwt}")
        assert jwt not in result
        assert "[REDACTED_TOKEN]" in result

    def test_ordinary_text_passes_through_unchanged(self) -> None:
        text = "How do I reset my password on the streaming dashboard?"
        assert redact_pii(text) == text

    def test_empty_string_returns_unchanged(self) -> None:
        assert redact_pii("") == ""

    def test_email_and_token_together_both_redacted(self) -> None:
        result = redact_pii("Email jane@example.com, key sk-abcdefghijklmnopqrstuvwxyz")
        assert "jane@example.com" not in result
        assert "sk-abcdefghijklmnopqrstuvwxyz" not in result
        assert "[REDACTED_EMAIL]" in result
        assert "[REDACTED_TOKEN]" in result
