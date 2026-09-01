"""services/adapters/email.py -- SMTP send via aiosmtplib (mocked, no real network)."""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any

import aiosmtplib
import pytest

from services.action_target import ActionTarget
from services.adapters import email as email_adapter
from services.adapters.base import NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope

_SMTP_KWARGS = dict(
    smtp_host="smtp.example.com",
    smtp_port=587,
    smtp_user="user",
    smtp_password="pass",
    smtp_use_tls=True,
    smtp_from_addr="noreply@waddlebot.com",
    timeout_seconds=5.0,
)


def _envelope() -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload={"event": "raid", "raider": "bob"},
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def _target() -> ActionTarget:
    return ActionTarget(
        type="email",
        to_addrs=("ops@example.com",),
        subject_template="Raid from {{raider}}",
        body_template="{{raider}} raided with {{event}}",
    )


async def test_sends_rendered_subject_and_body(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    async def _fake_send(message: EmailMessage, **kwargs: Any) -> tuple:
        captured["message"] = message
        captured["kwargs"] = kwargs
        return ({}, "OK")

    monkeypatch.setattr(aiosmtplib, "send", _fake_send)

    result = await email_adapter.dispatch(_target(), _envelope(), **_SMTP_KWARGS)

    sent: EmailMessage = captured["message"]
    assert sent["Subject"] == "Raid from bob"
    assert sent["To"] == "ops@example.com"
    assert sent.get_content().strip() == "bob raided with raid"
    assert captured["kwargs"]["hostname"] == "smtp.example.com"
    assert result.target_type == "email"


async def test_auth_failure_is_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_send(message: EmailMessage, **kwargs: Any) -> tuple:
        raise aiosmtplib.SMTPAuthenticationError(535, "auth failed")

    monkeypatch.setattr(aiosmtplib, "send", _fake_send)

    with pytest.raises(NonRetryableDispatchError):
        await email_adapter.dispatch(_target(), _envelope(), **_SMTP_KWARGS)


async def test_recipients_refused_is_non_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_send(message: EmailMessage, **kwargs: Any) -> tuple:
        # aiosmtplib>=5.x shape: list[SMTPRecipientRefused], not the 3.x
        # dict[str, tuple[int, str]] -- see email.py's module docstring.
        refused = aiosmtplib.SMTPRecipientRefused(550, "no such user", "ops@example.com")
        raise aiosmtplib.SMTPRecipientsRefused([refused])

    monkeypatch.setattr(aiosmtplib, "send", _fake_send)

    with pytest.raises(NonRetryableDispatchError):
        await email_adapter.dispatch(_target(), _envelope(), **_SMTP_KWARGS)


async def test_connect_error_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_send(message: EmailMessage, **kwargs: Any) -> tuple:
        raise aiosmtplib.SMTPConnectError("connection refused")

    monkeypatch.setattr(aiosmtplib, "send", _fake_send)

    with pytest.raises(RetryableDispatchError):
        await email_adapter.dispatch(_target(), _envelope(), **_SMTP_KWARGS)


async def test_generic_smtp_exception_is_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_send(message: EmailMessage, **kwargs: Any) -> tuple:
        raise aiosmtplib.SMTPException("transient failure")

    monkeypatch.setattr(aiosmtplib, "send", _fake_send)

    with pytest.raises(RetryableDispatchError):
        await email_adapter.dispatch(_target(), _envelope(), **_SMTP_KWARGS)
