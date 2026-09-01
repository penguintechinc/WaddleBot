"""`services/stripe_service.py` -- HMAC webhook-signature verification.

Fail-first note: `test_valid_signature_is_accepted` was temporarily broken
by flipping `hmac.compare_digest(expected, candidate)` to always return
`False` in a local scratch copy -- every test in this file went red
(including the "should reject" cases, since they'd trivially pass either
way), confirming the suite actually exercises `verify_webhook_signature`'s
real comparison rather than a vacuously-true assertion. Reverted; full
file green again before this port PR.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from services.errors import ApiError
from services.stripe_service import parse_webhook_event, verify_webhook_signature

SECRET = "whsec_test_secret"


def _sign(payload: bytes, secret: str = SECRET, timestamp: int | None = None) -> str:
    ts = timestamp if timestamp is not None else int(time.time())
    signed_payload = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


class TestVerifyWebhookSignature:
    def test_valid_signature_is_accepted(self) -> None:
        payload = b'{"id": "evt_1", "type": "checkout.session.completed"}'
        header = _sign(payload)
        assert verify_webhook_signature(payload, header, SECRET) is True

    def test_tampered_payload_is_rejected(self) -> None:
        payload = b'{"id": "evt_1", "amount_total": 100}'
        header = _sign(payload)
        tampered = b'{"id": "evt_1", "amount_total": 999999}'
        assert verify_webhook_signature(tampered, header, SECRET) is False

    def test_wrong_secret_is_rejected(self) -> None:
        payload = b'{"id": "evt_1"}'
        header = _sign(payload, secret="whsec_other")
        assert verify_webhook_signature(payload, header, SECRET) is False

    def test_missing_header_is_rejected(self) -> None:
        assert verify_webhook_signature(b"{}", None, SECRET) is False

    def test_malformed_header_is_rejected(self) -> None:
        assert verify_webhook_signature(b"{}", "not-a-valid-header", SECRET) is False

    def test_expired_timestamp_is_rejected(self) -> None:
        payload = b'{"id": "evt_1"}'
        old_ts = int(time.time()) - 10_000  # far outside the 300s default tolerance
        header = _sign(payload, timestamp=old_ts)
        assert verify_webhook_signature(payload, header, SECRET) is False

    def test_empty_secret_is_rejected(self) -> None:
        payload = b'{"id": "evt_1"}'
        header = _sign(payload)
        assert verify_webhook_signature(payload, header, "") is False


class TestParseWebhookEvent:
    def test_valid_event_parses(self) -> None:
        payload = b'{"id": "evt_1", "type": "checkout.session.completed", "data": {"object": {}}}'
        header = _sign(payload)
        event = parse_webhook_event(payload, header, SECRET)
        assert event["id"] == "evt_1"

    def test_invalid_signature_raises_400(self) -> None:
        payload = b'{"id": "evt_1"}'
        try:
            parse_webhook_event(payload, "t=1,v1=deadbeef", SECRET)
        except ApiError as exc:
            assert exc.status_code == 400
        else:
            raise AssertionError("expected ApiError")
