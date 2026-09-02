"""Token Crypto Tests.

`refresh_service.py` previously read and re-wrote OAuth `access_token`/
`refresh_token`/`client_secret` as plaintext (SECURITY HIGH). This suite
covers `token_crypto`'s AES-256-GCM round trip, tamper detection, and the
backward-compat `decrypt_if_needed` boundary that lets pre-existing
plaintext rows keep working until their next refresh.

Fail-first proof: with `refresh_service.RefreshService._update_tokens`
temporarily reverted to write `new_tokens["access_token"]`/
`new_tokens["refresh_token"]` directly (no `encrypt_value` call, no
`is_encrypted = TRUE`), `test_update_tokens_persists_ciphertext_not_plaintext`
went green->red as expected (the captured SQL parameter was the plaintext
literal, not ciphertext). Reverted after confirming; see PR report for the
exact before/after run.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault(
    "CREDENTIAL_ENCRYPTION_KEY", "d4f9317783becee1a4415c1a1229b9258e7a90b768d72a9e2c7dc891af661df6"
)
assert len(os.environ["CREDENTIAL_ENCRYPTION_KEY"]) == 64  # noqa: S101 - guards a test fixture value

from .token_crypto import (  # noqa: E402 - env var must be set before token_crypto is used
    TokenCryptoError,
    decrypt_if_needed,
    decrypt_value,
    encrypt_value,
)


class TestEncryptDecryptRoundTrip:
    def test_round_trip(self) -> None:
        plaintext = "wa_secret_oauth_token_12345"
        ciphertext = encrypt_value(plaintext)
        assert ciphertext != plaintext
        assert decrypt_value(ciphertext) == plaintext

    def test_ciphertext_is_not_plaintext_substring(self) -> None:
        """The plaintext must never appear anywhere in the stored ciphertext."""
        plaintext = "super-secret-refresh-token"
        ciphertext = encrypt_value(plaintext)
        assert plaintext not in ciphertext

    def test_two_encryptions_of_same_value_differ(self) -> None:
        """Random IV per call -- same plaintext never produces identical ciphertext twice."""
        plaintext = "same-token-both-times"
        assert encrypt_value(plaintext) != encrypt_value(plaintext)

    def test_tampered_ciphertext_raises(self) -> None:
        ciphertext = encrypt_value("token")
        tampered = ciphertext[:-4] + ("AAAA" if ciphertext[-4:] != "AAAA" else "BBBB")
        with pytest.raises(TokenCryptoError):
            decrypt_value(tampered)

    def test_garbage_input_raises(self) -> None:
        with pytest.raises(TokenCryptoError):
            decrypt_value("not-valid-base64-ciphertext!!!")

    def test_missing_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CREDENTIAL_ENCRYPTION_KEY", raising=False)
        with pytest.raises(TokenCryptoError):
            encrypt_value("token")

    def test_malformed_key_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CREDENTIAL_ENCRYPTION_KEY", "too-short")
        with pytest.raises(TokenCryptoError):
            encrypt_value("token")


class TestDecryptIfNeeded:
    def test_encrypted_row_is_decrypted(self) -> None:
        ciphertext = encrypt_value("plain-value")
        assert decrypt_if_needed(ciphertext, is_encrypted=True) == "plain-value"

    def test_legacy_plaintext_row_passes_through_unchanged(self) -> None:
        """Backward compat -- pre-fix rows (is_encrypted=False) are used as-is."""
        result = decrypt_if_needed("legacy-plaintext-token", is_encrypted=False)
        assert result == "legacy-plaintext-token"

    def test_none_value_passes_through(self) -> None:
        assert decrypt_if_needed(None, is_encrypted=True) is None

    def test_empty_string_passes_through(self) -> None:
        assert decrypt_if_needed("", is_encrypted=True) == ""

    def test_corrupt_encrypted_row_falls_back_to_raw_value_not_raise(self) -> None:
        """A row that claims is_encrypted=True but holds corrupt data logs and returns as-is."""
        result = decrypt_if_needed("corrupt-not-real-ciphertext", is_encrypted=True)
        assert result == "corrupt-not-real-ciphertext"
