"""services/signing.py -- secret resolution + HMAC-SHA256 signing."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from services.signing import SecretResolutionError, resolve_secret, sign_body


def test_resolve_secret_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_WEBHOOK_SECRET", "s3cr3t")
    assert resolve_secret("MY_WEBHOOK_SECRET") == "s3cr3t"


def test_resolve_secret_raises_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("UNSET_SECRET_REF", raising=False)
    with pytest.raises(SecretResolutionError, match="UNSET_SECRET_REF"):
        resolve_secret("UNSET_SECRET_REF")


def test_resolve_secret_raises_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMPTY_SECRET_REF", "")
    with pytest.raises(SecretResolutionError):
        resolve_secret("EMPTY_SECRET_REF")


def test_sign_body_matches_reference_hmac() -> None:
    body = b'{"hello":"world"}'
    signature = sign_body("s3cr3t", body)
    expected = hmac.new(b"s3cr3t", body, hashlib.sha256).hexdigest()
    assert signature == expected


def test_sign_body_differs_for_different_secrets() -> None:
    body = b"payload"
    assert sign_body("secret-a", body) != sign_body("secret-b", body)
