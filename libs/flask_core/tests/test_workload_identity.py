"""
Tests for flask_core.workload_identity (SPIFFE/SPIRE workload identity).

The load-bearing assertion here is that a peer holding a *valid, legitimately
issued* SVID that is NOT on the callee's allowlist is REJECTED. An mTLS
requirement that has never rejected a legitimately-issued identity is not known
to authorize anything — presenting an identity and verifying the other end's
are different things.

Fail-on-purpose proof (see FAIL_ON_PURPOSE below): the svc-core matcher used by
``test_unlisted_peer_is_rejected`` is built through ``_build_svc_core_matcher``,
which honors the ``WADDLE_SPIFFE_TEST_PERMISSIVE`` env toggle. With the toggle
ON the matcher degrades to ``allow_trust_domain("penguintech.io")`` — the exact
"accept anything holding a penguintech.io SVID" bug the matcher exists to close
— and the unlisted-peer test FAILS. With it OFF (the default, and the real
policy) svc-core admits only the three stages and the test PASSES. Run:

    WADDLE_SPIFFE_TEST_PERMISSIVE=1 pytest .../test_workload_identity.py \\
        -k unlisted_peer_is_rejected            # -> 1 failed  (bug simulated)
    pytest .../test_workload_identity.py                       # -> all passed

NOTE — mTLS does NOT replace the inter-service JWT. Per security.md every
inter-service call carries a short-lived signed JWT regardless of transport.
The SVID/matcher checked here answers "which workload is calling"; the machine
JWT (a separate gate, not exercised by authorize_peer) answers "what may it
do". See ``test_peer_authorization_is_independent_of_the_jwt_gate``.
"""

import os

import pytest

from flask_core.workload_identity import (
    Degraded,
    EmptyTrustBundle,
    IdentityProvider,
    JwtSvid,
    NoDefaultSvid,
    PeerNotAuthorized,
    SpiffeId,
    SpiffeIdMatcher,
    TrustBundleSet,
    TrustDomain,
    WorkloadApiSource,
    WorkloadApiUnavailable,
    X509Context,
    X509Svid,
)

TRUST_DOMAIN = "penguintech.io"
ENV = "alpha"


def sid(service: str) -> str:
    """Build a house-pattern SPIFFE ID string for ``service`` in the test env."""
    return f"spiffe://{TRUST_DOMAIN}/{ENV}/{service}"


def _svid(service: str) -> X509Svid:
    """Build a placeholder X.509-SVID for ``service`` (PEM bytes are opaque here)."""
    return X509Svid(
        spiffe_id=SpiffeId.parse(sid(service)),
        cert_chain_pem=b"-----BEGIN CERTIFICATE-----\nfake\n-----END CERTIFICATE-----",
        private_key_pem=b"-----BEGIN PRIVATE KEY-----\nfake\n-----END PRIVATE KEY-----",
    )


def _bundles() -> TrustBundleSet:
    """A non-empty trust bundle set for the trust domain."""
    return TrustBundleSet({TRUST_DOMAIN: b"-----BEGIN CERTIFICATE-----\nca\n-----END CERTIFICATE-----"})


class FakeWorkloadApiSource(WorkloadApiSource):
    """
    In-memory Workload API stand-in so tests exercise IdentityProvider's
    attestation and fail-safe logic without a live SPIRE agent socket.
    """

    def __init__(self, context=None, jwt=None, error: Exception | None = None):
        """Hold a canned X.509 context / JWT-SVID, or an error to raise on fetch."""
        self._context = context
        self._jwt = jwt
        self._error = error

    def fetch_x509_context(self) -> X509Context:
        """Return the canned context, or raise the canned error."""
        if self._error is not None:
            raise self._error
        return self._context

    def fetch_jwt_svid(self, audience: str) -> JwtSvid:
        """Return the canned JWT-SVID, or raise the canned error."""
        if self._error is not None:
            raise self._error
        return self._jwt


# svc-core's real policy: it accepts calls from the three pipeline stages only,
# NOT from anything else holding a penguintech.io SVID (e.g. hub-webui).
STAGES = ("svc-ingest", "svc-process", "svc-action")
UNLISTED = "hub-webui"

FAIL_ON_PURPOSE = os.environ.get("WADDLE_SPIFFE_TEST_PERMISSIVE") == "1"


def _build_svc_core_matcher() -> SpiffeIdMatcher:
    """
    Build svc-core's accepted-peer allowlist. Default (correct) policy admits
    only the three stages by exact SPIFFE ID. The WADDLE_SPIFFE_TEST_PERMISSIVE
    toggle swaps in the broken "allow the whole trust domain" policy so the
    unlisted-peer test can be made to fail on purpose (see module docstring).
    """
    if FAIL_ON_PURPOSE:
        return SpiffeIdMatcher().allow_trust_domain(TRUST_DOMAIN)
    matcher = SpiffeIdMatcher()
    for stage in STAGES:
        matcher.allow_exact(sid(stage))
    return matcher


def _provider_with_identity(service: str = "svc-core") -> IdentityProvider:
    """An IdentityProvider holding a real identity for ``service`` via a fake source."""
    ctx = X509Context(default_svid=_svid(service), bundles=_bundles())
    return IdentityProvider.connect(source=FakeWorkloadApiSource(context=ctx), require=True)


# --------------------------------------------------------------------------
# The three assertions the task requires, expressed against the mTLS config.
# --------------------------------------------------------------------------
@pytest.mark.parametrize("stage", STAGES)
def test_listed_peer_is_accepted(stage):
    """A stage on svc-core's allowlist passes authorization."""
    cfg = _provider_with_identity().server_tls_config(_build_svc_core_matcher())
    cfg.authorize_peer(sid(stage))  # must not raise


def test_unlisted_peer_is_rejected():
    """
    LOAD-BEARING: a peer holding a valid penguintech.io SVID that svc-core does
    NOT list (hub-webui) is rejected. Fails on purpose under
    WADDLE_SPIFFE_TEST_PERMISSIVE=1, which simulates a missing allowlist.
    """
    cfg = _provider_with_identity().server_tls_config(_build_svc_core_matcher())
    with pytest.raises(PeerNotAuthorized):
        cfg.authorize_peer(sid(UNLISTED))


def test_absent_svid_is_rejected():
    """A peer that presented no SVID at all (None) is rejected."""
    cfg = _provider_with_identity().server_tls_config(_build_svc_core_matcher())
    with pytest.raises(PeerNotAuthorized):
        cfg.authorize_peer(None)


# --------------------------------------------------------------------------
# Attestation-side "no SVID" and fail-safe behavior.
# --------------------------------------------------------------------------
def test_attestation_without_svid_hardfails_in_production():
    """A Workload API that issues no default SVID hard-fails in production posture."""
    ctx = X509Context(default_svid=None, bundles=_bundles())
    with pytest.raises(WorkloadApiUnavailable):
        IdentityProvider.connect(source=FakeWorkloadApiSource(context=ctx), require=True)


def test_unreachable_workload_api_degrades_outside_production():
    """Outside production an unreachable Workload API degrades instead of crashing."""
    src = FakeWorkloadApiSource(error=RuntimeError("socket refused"))
    provider = IdentityProvider.connect(source=src, require=False)
    assert provider.has_identity() is False
    with pytest.raises(Degraded):
        provider.server_tls_config(_build_svc_core_matcher())


def test_unreachable_workload_api_hardfails_in_production():
    """In production an unreachable Workload API hard-fails rather than degrading."""
    src = FakeWorkloadApiSource(error=RuntimeError("socket refused"))
    with pytest.raises(WorkloadApiUnavailable):
        IdentityProvider.connect(source=src, require=True)


def test_empty_trust_bundle_refuses_to_build_config():
    """A held identity with no trust authorities refuses to build a mTLS config."""
    ctx = X509Context(default_svid=_svid("svc-core"), bundles=TrustBundleSet({}))
    provider = IdentityProvider.connect(source=FakeWorkloadApiSource(context=ctx), require=True)
    assert provider.has_identity() is True
    with pytest.raises(EmptyTrustBundle):
        provider.client_tls_config(_build_svc_core_matcher())


def test_provider_exposes_own_spiffe_id():
    """The provider surfaces its own workload SPIFFE ID for logging/attestation checks."""
    provider = _provider_with_identity("svc-core")
    assert str(provider.spiffe_id()) == sid("svc-core")


# --------------------------------------------------------------------------
# mTLS is not the JWT gate.
# --------------------------------------------------------------------------
def test_peer_authorization_is_independent_of_the_jwt_gate():
    """
    Authorizing a peer's SVID does not fetch, validate, or imply the machine
    JWT. security.md requires the short-lived signed JWT on every inter-service
    call regardless of transport; a green authorize_peer is necessary, not
    sufficient — the caller must still enforce the JWT separately.
    """
    called = {"jwt": False}

    class JwtTrackingSource(FakeWorkloadApiSource):
        def fetch_jwt_svid(self, audience: str) -> JwtSvid:
            called["jwt"] = True
            return super().fetch_jwt_svid(audience)

    ctx = X509Context(default_svid=_svid("svc-core"), bundles=_bundles())
    provider = IdentityProvider.connect(source=JwtTrackingSource(context=ctx), require=True)
    cfg = provider.server_tls_config(_build_svc_core_matcher())
    cfg.authorize_peer(sid("svc-ingest"))
    assert called["jwt"] is False  # peer authz touched no JWT path


# --------------------------------------------------------------------------
# SpiffeIdMatcher unit tests (mirror skauswatch-identity's matcher tests).
# --------------------------------------------------------------------------
def test_empty_matcher_rejects_everything():
    """The default matcher has no rules and admits no peer — no implicit trust-all."""
    assert SpiffeIdMatcher().matches(sid("svc-ingest")) is False


def test_allow_trust_domain_matches_any_path_in_domain_only():
    """allow_trust_domain admits any path in the domain but nothing outside it."""
    matcher = SpiffeIdMatcher().allow_trust_domain(TRUST_DOMAIN)
    assert matcher.matches(sid("svc-ingest")) is True
    assert matcher.matches("spiffe://other.example/alpha/svc-ingest") is False


def test_allow_path_prefix_matches_segment_boundary_only():
    """A /alpha prefix matches /alpha and /alpha/x but never /alphainator."""
    matcher = SpiffeIdMatcher().allow_path_prefix(TRUST_DOMAIN, "/alpha")
    assert matcher.matches("spiffe://penguintech.io/alpha") is True
    assert matcher.matches(sid("svc-ingest")) is True
    assert matcher.matches("spiffe://penguintech.io/alphainator") is False
    assert matcher.matches("spiffe://penguintech.io/beta/svc-ingest") is False


def test_allow_path_prefix_normalizes_missing_leading_slash():
    """A prefix given without a leading slash behaves identically to one with it."""
    matcher = SpiffeIdMatcher().allow_path_prefix(TRUST_DOMAIN, "alpha")
    assert matcher.matches(sid("svc-ingest")) is True


def test_allow_exact_matches_only_that_id():
    """allow_exact admits exactly one SPIFFE ID and no sibling."""
    matcher = SpiffeIdMatcher().allow_exact(sid("svc-ingest"))
    assert matcher.matches(sid("svc-ingest")) is True
    assert matcher.matches(sid("svc-process")) is False


def test_matcher_spans_multiple_trust_domains_for_federation():
    """A matcher can admit more than one trust domain (federation)."""
    matcher = (
        SpiffeIdMatcher()
        .allow_trust_domain(TRUST_DOMAIN)
        .allow_trust_domain("customer.example")
    )
    assert matcher.matches(sid("svc-ingest")) is True
    assert matcher.matches("spiffe://customer.example/agent/x") is True
    assert matcher.matches("spiffe://unrelated.example/agent/x") is False


def test_spiffe_id_parse_rejects_malformed():
    """SpiffeId.parse rejects non-spiffe URIs and IDs missing a trust domain or path."""
    with pytest.raises(Exception):
        SpiffeId.parse("https://penguintech.io/alpha/x")
    with pytest.raises(Exception):
        SpiffeId.parse("spiffe://penguintech.io")


def test_trust_domain_membership():
    """SpiffeId.is_member_of reflects the authority component only."""
    parsed = SpiffeId.parse(sid("svc-core"))
    assert parsed.is_member_of(TrustDomain(TRUST_DOMAIN)) is True
    assert parsed.is_member_of(TrustDomain("other.example")) is False
