"""`services/marketplace_crypto.py` -- AES-256-GCM webhook-secret encryption."""

from __future__ import annotations

from typing import Any

import pytest

from services import marketplace_crypto as crypto


class TestRoundTrip:
    def test_encrypt_then_decrypt_recovers_plaintext(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("MARKETPLACE_ENCRYPTION_KEY", "a" * 64)
        stored = crypto.encrypt_webhook_secret("my-webhook-secret")
        assert stored != "my-webhook-secret"
        assert crypto.decrypt_webhook_secret(stored) == "my-webhook-secret"

    def test_two_encryptions_of_same_plaintext_differ(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("MARKETPLACE_ENCRYPTION_KEY", "b" * 64)
        first = crypto.encrypt_webhook_secret("same-secret")
        second = crypto.encrypt_webhook_secret("same-secret")
        assert first != second  # random IV per call


class TestFailsClosed:
    def test_missing_key_raises(self, monkeypatch: Any) -> None:
        monkeypatch.delenv("MARKETPLACE_ENCRYPTION_KEY", raising=False)
        with pytest.raises(crypto.MarketplaceEncryptionKeyError):
            crypto.encrypt_webhook_secret("x")

    def test_short_key_raises(self, monkeypatch: Any) -> None:
        monkeypatch.setenv("MARKETPLACE_ENCRYPTION_KEY", "tooshort")
        with pytest.raises(crypto.MarketplaceEncryptionKeyError):
            crypto.encrypt_webhook_secret("x")
