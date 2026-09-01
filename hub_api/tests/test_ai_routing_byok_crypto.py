"""`services/ai_routing/byok_crypto.py` -- AES-256-GCM round-trip, tamper detection, key hygiene.

No mocking -- this is the real `cryptography` primitive end-to-end.
"""

from __future__ import annotations

import pytest

from services.ai_routing.byok_crypto import decrypt_key, encrypt_key, mask_key
from services.errors import ApiError

_VALID_KEY_HEX = "aa" * 32


class TestEncryptionKeyValidation:
    def test_missing_env_var_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AI_BYOK_ENCRYPTION_KEY", raising=False)
        with pytest.raises(ApiError) as exc_info:
            encrypt_key("sk-whatever")
        assert exc_info.value.status_code == 500

    def test_non_hex_value_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", "not-hex-at-all-zzzz")
        with pytest.raises(ApiError):
            encrypt_key("sk-whatever")

    def test_wrong_length_hex_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", "aa" * 10)  # too short
        with pytest.raises(ApiError):
            encrypt_key("sk-whatever")


class TestEncryptDecryptRoundTrip:
    def test_round_trips_exactly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", _VALID_KEY_HEX)
        ciphertext = encrypt_key("sk-my-real-api-key-value")
        assert "sk-my-real-api-key-value" not in ciphertext
        assert decrypt_key(ciphertext) == "sk-my-real-api-key-value"

    def test_two_encryptions_of_same_plaintext_differ(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Random IV per call -- ciphertext must not be deterministic."""
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", _VALID_KEY_HEX)
        first = encrypt_key("sk-same-value")
        second = encrypt_key("sk-same-value")
        assert first != second

    def test_tampered_ciphertext_fails_to_decrypt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", _VALID_KEY_HEX)
        ciphertext = encrypt_key("sk-original")
        tampered = ciphertext[:-4] + ("A" if ciphertext[-4] != "A" else "B") + ciphertext[-3:]
        with pytest.raises(ApiError) as exc_info:
            decrypt_key(tampered)
        assert exc_info.value.status_code == 500

    def test_wrong_key_fails_to_decrypt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", _VALID_KEY_HEX)
        ciphertext = encrypt_key("sk-original")
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", "bb" * 32)
        with pytest.raises(ApiError):
            decrypt_key(ciphertext)

    def test_malformed_base64_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AI_BYOK_ENCRYPTION_KEY", _VALID_KEY_HEX)
        with pytest.raises(ApiError):
            decrypt_key("not valid base64 at all !!!")


class TestMaskKey:
    def test_returns_last_four_chars(self) -> None:
        assert mask_key("sk-abcdef1234") == "1234"

    def test_short_key_returns_placeholder(self) -> None:
        assert mask_key("abc") == "****"

    def test_empty_key_returns_placeholder(self) -> None:
        assert mask_key("") == "****"
