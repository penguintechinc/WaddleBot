"""
Tests for flask_core.auth's JWT issuer/audience validation and required-claims
enforcement (HIGH security fix: `verify_jwt_token` previously carried no
`iss`/`aud` claims at all and did no audience check).

The load-bearing assertion: a token whose `iss`/`aud` claim is PRESENT but
does NOT match what the verifier expects is rejected outright (cross-service
replay / audience-confusion). A token missing either claim entirely (minted
by `create_jwt_token()` before this fix landed) still verifies -- mirroring
the same bounded-migration posture the existing `tenant` claim handling in
this module already uses, since every JWT here expires within 24h anyway
(security.md's own JWT ceiling), so there is no long-lived legacy token to
carry indefinitely.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from flask_core.auth import (
    DEFAULT_JWT_AUDIENCE,
    DEFAULT_JWT_ISSUER,
    create_jwt_token,
    verify_jwt_token,
)

SECRET = "test-secret-key-not-for-production-use-only"


def _valid_payload(**overrides):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "u1",
        "username": "alice",
        "email": "alice@example.com",
        "roles": [],
        "tenant": "global",
        "scope": "",
        "iat": now,
        "exp": now + timedelta(hours=1),
        "type": "access",
    }
    payload.update(overrides)
    return payload


class TestCreateJwtTokenEmitsIssAudTeams:
    def test_default_issuer_and_audience_emitted(self):
        token = create_jwt_token(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            roles=["viewer"],
            secret_key=SECRET,
            tenant="global",
        )
        decoded = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})
        assert decoded["iss"] == DEFAULT_JWT_ISSUER
        assert decoded["aud"] == DEFAULT_JWT_AUDIENCE
        assert decoded["teams"] == []

    def test_teams_claim_passed_through(self):
        token = create_jwt_token(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            roles=["viewer"],
            secret_key=SECRET,
            tenant="global",
            teams=["team-a", "team-b"],
        )
        decoded = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})
        assert decoded["teams"] == ["team-a", "team-b"]

    def test_custom_issuer_and_audience(self):
        token = create_jwt_token(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            roles=[],
            secret_key=SECRET,
            tenant="global",
            issuer="custom-issuer",
            audience="custom-audience",
        )
        decoded = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_aud": False})
        assert decoded["iss"] == "custom-issuer"
        assert decoded["aud"] == "custom-audience"


class TestVerifyJwtTokenRoundTrip:
    def test_create_and_verify_round_trip_passes_default_iss_aud(self):
        token = create_jwt_token(
            user_id="u1",
            username="alice",
            email="alice@example.com",
            roles=["viewer"],
            secret_key=SECRET,
            tenant="global",
        )
        payload = verify_jwt_token(token, SECRET)
        assert payload is not None
        assert payload["iss"] == DEFAULT_JWT_ISSUER
        assert payload["aud"] == DEFAULT_JWT_AUDIENCE


class TestIssuerAudienceMismatchRejected:
    """The HIGH fix's centerpiece: PRESENT-but-WRONG iss/aud is rejected."""

    def test_wrong_issuer_rejected(self):
        payload = _valid_payload(iss="some-other-service", aud=DEFAULT_JWT_AUDIENCE)
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is None

    def test_wrong_audience_rejected(self):
        payload = _valid_payload(iss=DEFAULT_JWT_ISSUER, aud="some-other-audience")
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is None

    def test_wrong_issuer_and_audience_rejected(self):
        payload = _valid_payload(iss="attacker-service", aud="attacker-audience")
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is None

    def test_custom_expected_issuer_and_audience_enforced(self):
        """A verifier that expects non-default iss/aud rejects the platform default too."""
        payload = _valid_payload(iss=DEFAULT_JWT_ISSUER, aud=DEFAULT_JWT_AUDIENCE)
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        result = verify_jwt_token(
            token, SECRET, issuer="other-issuer", audience="other-audience"
        )
        assert result is None


class TestIssuerAudienceAbsenceStillVerifies:
    """A legacy token minted before this fix (no iss/aud at all) is not rejected --
    bounded by the 24h JWT ceiling rather than a second timed migration cutoff."""

    def test_missing_iss_and_aud_still_verifies(self):
        payload = _valid_payload()  # no iss/aud keys at all
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        result = verify_jwt_token(token, SECRET)
        assert result is not None
        assert result["sub"] == "u1"

    def test_present_iss_missing_aud_still_verifies(self):
        payload = _valid_payload(iss=DEFAULT_JWT_ISSUER)
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is not None

    def test_missing_iss_present_correct_aud_still_verifies(self):
        payload = _valid_payload(aud=DEFAULT_JWT_AUDIENCE)
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is not None


class TestRequiredClaimsEnforcement:
    """A token missing sub/iat/exp fails closed (401-shaped None) instead of a raw
    KeyError 500 -- the previous behavior for `payload['exp']` on a malformed token."""

    def test_missing_exp_rejected_cleanly(self):
        payload = _valid_payload()
        del payload["exp"]
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is None

    def test_missing_sub_rejected_cleanly(self):
        payload = _valid_payload()
        del payload["sub"]
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is None

    def test_missing_iat_rejected_cleanly(self):
        payload = _valid_payload()
        del payload["iat"]
        token = jwt.encode(payload, SECRET, algorithm="HS256")
        assert verify_jwt_token(token, SECRET) is None
