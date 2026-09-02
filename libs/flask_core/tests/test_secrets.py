"""
Tests for flask_core.secrets (C1 security fix: fail-closed SECRET_KEY loading).

The load-bearing assertion: `require_secret_key()` REFUSES to return an
unset/placeholder value once production posture is forced on (`require=True`)
-- exactly the deploy that previously booted silently with a publicly known
JWT signing key (`change-me-in-production`), letting anyone forge a
`global:admin` or arbitrary-`tenant` token against every service sharing it.

`require=True` (not environment-variable gymnastics) is how these tests force
production posture -- the same override shape `workload_identity.
IdentityProvider.connect(require=...)` already uses for its own fail-safe
check. This also proves the "raise" path is real: without it, a live pytest
process is *never* treated as production (see
`test_default_resolution_never_fails_closed_under_pytest`), which is what
keeps every OTHER test suite in this repo passing unmodified even though
their fixtures literally use the placeholder string as a fixed test secret.
"""

from __future__ import annotations

import pytest

from flask_core.secrets import (
    KNOWN_PLACEHOLDER_SECRETS,
    InsecureSecretError,
    require_secret_key,
)


class TestFailsClosedInProduction:
    """`require=True` forces production posture regardless of the real environment."""

    def test_unset_secret_key_refuses_to_start(self, monkeypatch):
        """No SECRET_KEY at all, in production -- must raise, not return a default."""
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with pytest.raises(InsecureSecretError, match="SECRET_KEY"):
            require_secret_key(require=True)

    def test_placeholder_secret_key_refuses_to_start(self, monkeypatch):
        """SECRET_KEY explicitly set to the known placeholder, in production -- must raise."""
        monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
        with pytest.raises(InsecureSecretError):
            require_secret_key(require=True)

    def test_empty_string_secret_key_refuses_to_start(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "")
        with pytest.raises(InsecureSecretError):
            require_secret_key(require=True)

    def test_real_secret_key_passes_in_production(self, monkeypatch):
        """A real, non-placeholder value in production -- returns it, does not raise."""
        monkeypatch.setenv("SECRET_KEY", "a-real-randomly-generated-secret-value")
        assert require_secret_key(require=True) == "a-real-randomly-generated-secret-value"

    def test_custom_env_var_name_also_fails_closed(self, monkeypatch):
        """Non-default env var names (MODULE_SECRET_KEY, API_KEY, ...) get the same treatment."""
        monkeypatch.delenv("MODULE_SECRET_KEY", raising=False)
        with pytest.raises(InsecureSecretError, match="MODULE_SECRET_KEY"):
            require_secret_key("MODULE_SECRET_KEY", require=True)

    def test_custom_default_placeholder_also_rejected(self, monkeypatch):
        """A caller-supplied `default` (e.g. video_proxy_module's own JWT_SECRET_KEY
        spelling) is checked against KNOWN_PLACEHOLDER_SECRETS the same way."""
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        with pytest.raises(InsecureSecretError):
            require_secret_key(
                "JWT_SECRET_KEY", default="jwt-secret-change-in-production", require=True
            )


class TestDoesNotBreakDevAndTestUsage:
    """Outside production, the historical placeholder-returning behavior is unchanged."""

    def test_unset_secret_key_returns_placeholder_outside_production(self, monkeypatch):
        monkeypatch.delenv("SECRET_KEY", raising=False)
        assert require_secret_key(require=False) == "change-me-in-production"

    def test_default_resolution_never_fails_closed_under_pytest(self, monkeypatch):
        """The default (`require=None`) resolution path -- what every Config class
        body across ~40 services actually calls -- never raises while pytest is
        running, even with SECRET_KEY completely unset. This is what keeps every
        pre-existing test suite in this repo green without editing ~50 conftest
        files to set RELEASE_MODE/ENVIRONMENT."""
        monkeypatch.delenv("SECRET_KEY", raising=False)
        monkeypatch.delenv("RELEASE_MODE", raising=False)
        monkeypatch.delenv("WADDLEBOT_ENV", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("NODE_ENV", raising=False)
        assert require_secret_key() == "change-me-in-production"

    def test_real_value_still_returned_when_set_outside_production(self, monkeypatch):
        monkeypatch.setenv("SECRET_KEY", "dev-value-not-a-placeholder")
        assert require_secret_key(require=False) == "dev-value-not-a-placeholder"


class TestKnownPlaceholderSecrets:
    """The centralized placeholder set the C1 grep audit found across the repo."""

    @pytest.mark.parametrize(
        "placeholder",
        [
            "change-me-in-production",
            "jwt-secret-key-change-in-prod",
            "jwt-secret-change-in-production",
            "development-secret-key",
            "your-secret-key-change-in-production",
            "",
        ],
    )
    def test_every_known_placeholder_is_registered(self, placeholder):
        assert placeholder in KNOWN_PLACEHOLDER_SECRETS
