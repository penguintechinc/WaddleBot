"""`email` action-target adapter -- real SMTP send via aiosmtplib.

`SMTP_*` env vars (config.py) provide the outbound relay; `to_addrs`/
`subject_template`/`body_template` come from the bundle's `action_target`
config, rendered against the envelope payload (services/templating.py).
"""

from __future__ import annotations

from email.message import EmailMessage

import aiosmtplib

from services.action_target import ActionTarget
from services.adapters.base import AdapterResult, NonRetryableDispatchError, RetryableDispatchError
from services.envelope import ActionEnvelope
from services.templating import render_template


async def dispatch(
    target: ActionTarget,
    envelope: ActionEnvelope,
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    smtp_use_tls: bool,
    smtp_from_addr: str,
    timeout_seconds: float,
) -> AdapterResult:
    """Send one email via SMTP.

    Raises :class:`NonRetryableDispatchError` on authentication failure or
    a rejected recipient (both config-shaped, not transient);
    :class:`RetryableDispatchError` on connection/timeout/generic SMTP
    errors -- the relay may simply be temporarily unreachable.
    """
    subject = render_template(target.subject_template, envelope.payload)
    body = render_template(target.body_template, envelope.payload) if target.body_template else ""

    message = EmailMessage()
    message["From"] = smtp_from_addr
    message["To"] = ", ".join(target.to_addrs)
    message["Subject"] = subject
    message.set_content(body)

    try:
        response = await aiosmtplib.send(
            message,
            hostname=smtp_host,
            port=smtp_port,
            username=smtp_user or None,
            password=smtp_password or None,
            start_tls=smtp_use_tls,
            timeout=timeout_seconds,
        )
    except aiosmtplib.SMTPAuthenticationError as exc:
        raise NonRetryableDispatchError(f"email SMTP auth failed: {exc}") from exc
    except aiosmtplib.SMTPRecipientsRefused as exc:
        raise NonRetryableDispatchError(f"email recipients refused: {exc}") from exc
    except (
        aiosmtplib.SMTPConnectError,
        aiosmtplib.SMTPServerDisconnected,
        aiosmtplib.SMTPTimeoutError,
        TimeoutError,
        OSError,
    ) as exc:
        raise RetryableDispatchError(f"email SMTP connection failed: {exc}") from exc
    except aiosmtplib.SMTPException as exc:
        raise RetryableDispatchError(f"email SMTP send failed: {exc}") from exc

    return AdapterResult(
        target_type="email",
        detail=f"sent to {len(target.to_addrs)} recipient(s): {response!r}",
    )
