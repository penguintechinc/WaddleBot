"""
SPIFFE/SPIRE workload identity for Waddles services.
=====================================================

Python port of the shape proven in ``skauswatch-identity`` (Rust). Two
responsibilities, deliberately kept separate because the second is the one
easy to omit:

- :class:`IdentityProvider` attests to the local SPIFFE Workload API socket
  (named by ``SPIFFE_ENDPOINT_SOCKET``), holds the X.509-SVID and trust
  bundle set, and builds mTLS configs from them.
- :class:`SpiffeIdMatcher` is a **caller-supplied allowlist enforced against
  the PEER's SPIFFE ID**. Presenting an identity and verifying the other
  end's are different things: without the matcher, mTLS proves only that the
  peer holds *some* valid SVID in the trust domain, so every workload in the
  mesh passes. Each service declares which peer SPIFFE IDs it accepts.

mTLS does **not** replace the inter-service JWT. Per ``security.md``, every
inter-service call still carries a short-lived signed JWT regardless of
transport (gRPC or REST), whether or not SPIFFE is live for that call. This
module authenticates *which workload* is calling; the JWT authorizes *what
that call may do*. They compose; neither substitutes for the other. An SVID
also does not carry tenancy — it composes with the per-(tenant, stage) ACL
users, it does not replace them.

SDK note: the ``spiffe`` (py-spiffe) package provides the real Workload API
client and X.509 URI-SAN parsing. It is not a hard dependency of this module
so the load-bearing matcher/authorization logic stays fully testable in pure
Python. Where the SDK is required (live socket attestation, extracting a peer
SPIFFE ID from a real certificate) the seam is a documented ``TODO`` and an
injectable :class:`WorkloadApiSource`, so tests substitute a fake source.
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

SPIFFE_ENDPOINT_SOCKET_ENV = "SPIFFE_ENDPOINT_SOCKET"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
class IdentityError(Exception):
    """Base class for every workload-identity failure raised by this module."""


class SpiffeIdError(IdentityError):
    """A string could not be parsed as a valid SPIFFE ID or trust domain."""


class WorkloadApiUnavailable(IdentityError):
    """
    The Workload API was unreachable (or issued no usable SVID) while running
    in production posture. Startup must not proceed as if validly attested.
    """


class Degraded(IdentityError):
    """
    No workload identity is currently held — attestation degraded outside
    production, or a refresh has not yet succeeded. Callers must not build
    mTLS configs or fetch JWT-SVIDs while degraded.
    """


class NoDefaultSvid(IdentityError):
    """The Workload API returned an X.509 context with no SVID for this workload."""


class EmptyTrustBundle(IdentityError):
    """
    The held trust bundle set has no authorities, so a mTLS config built from
    it could validate no peer — building one is refused rather than silently
    trusting nothing.
    """


class JwtSvidError(IdentityError):
    """Fetching a JWT-SVID from the Workload API failed."""


class PeerNotAuthorized(IdentityError):
    """
    A peer presented a valid SVID whose SPIFFE ID is not on the callee's
    allowlist. This is the failure the :class:`SpiffeIdMatcher` exists to
    raise — a missing matcher would let this peer through.
    """


# ---------------------------------------------------------------------------
# SPIFFE value types (pure-Python, no SDK required)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TrustDomain:
    """A SPIFFE trust domain (the authority part of a SPIFFE ID, e.g. ``penguintech.io``)."""

    name: str

    def __post_init__(self) -> None:
        """Validate the trust-domain name is present and scheme/path-free."""
        if not self.name or "/" in self.name or "://" in self.name:
            raise SpiffeIdError(f"invalid trust domain: {self.name!r}")

    def __str__(self) -> str:  # noqa: D105 - trivial
        return self.name


@dataclass(frozen=True, slots=True)
class SpiffeId:
    """
    A parsed SPIFFE ID (``spiffe://<trust_domain>/<path>``). Holds the trust
    domain and the ``/``-prefixed path, and knows its own trust-domain
    membership — the two facts the matcher decides on.
    """

    trust_domain: TrustDomain
    path: str

    @classmethod
    def parse(cls, uri: str) -> "SpiffeId":
        """Parse a ``spiffe://`` URI into a :class:`SpiffeId`, or raise :class:`SpiffeIdError`."""
        scheme = "spiffe://"
        if not uri.startswith(scheme):
            raise SpiffeIdError(f"not a spiffe:// URI: {uri!r}")
        rest = uri[len(scheme):]
        authority, slash, path = rest.partition("/")
        if not authority:
            raise SpiffeIdError(f"spiffe ID has no trust domain: {uri!r}")
        if not slash:
            raise SpiffeIdError(f"spiffe ID has no path: {uri!r}")
        return cls(TrustDomain(authority), "/" + path)

    def is_member_of(self, trust_domain: TrustDomain) -> bool:
        """Whether this SPIFFE ID belongs to ``trust_domain``."""
        return self.trust_domain == trust_domain

    def __str__(self) -> str:  # noqa: D105 - trivial
        return f"spiffe://{self.trust_domain}{self.path}"


# ---------------------------------------------------------------------------
# SpiffeIdMatcher — the load-bearing allowlist
# ---------------------------------------------------------------------------
def _path_has_prefix(path: str, prefix: str) -> bool:
    """
    Segment-boundary prefix match: ``/beta`` matches ``/beta`` and
    ``/beta/manager`` but never ``/betainator`` — whole ``/``-delimited
    segments, not a raw byte prefix.
    """
    if path == prefix:
        return True
    if path.startswith(prefix):
        return path[len(prefix):].startswith("/")
    return False


@dataclass(frozen=True, slots=True)
class _AnyPath:
    """Allow-rule: any SPIFFE ID in this trust domain, regardless of path."""

    trust_domain: TrustDomain

    def matches(self, spiffe_id: SpiffeId) -> bool:
        """Whether ``spiffe_id`` is a member of this rule's trust domain."""
        return spiffe_id.is_member_of(self.trust_domain)


@dataclass(frozen=True, slots=True)
class _PathPrefix:
    """Allow-rule: IDs in this trust domain whose path starts with ``prefix``."""

    trust_domain: TrustDomain
    prefix: str

    def matches(self, spiffe_id: SpiffeId) -> bool:
        """Whether ``spiffe_id`` is in the trust domain and its path has the prefix."""
        return spiffe_id.is_member_of(self.trust_domain) and _path_has_prefix(
            spiffe_id.path, self.prefix
        )


@dataclass(frozen=True, slots=True)
class _Exact:
    """Allow-rule: exactly one SPIFFE ID."""

    spiffe_id: SpiffeId

    def matches(self, spiffe_id: SpiffeId) -> bool:
        """Whether ``spiffe_id`` equals the single permitted ID."""
        return spiffe_id == self.spiffe_id


class SpiffeIdMatcher:
    """
    An allowlist of SPIFFE IDs a mTLS peer's certificate may present.

    Built with :meth:`allow_trust_domain`, :meth:`allow_path_prefix`, and
    :meth:`allow_exact`; a peer matches if it satisfies *any* configured rule.
    An empty matcher (the default) matches nothing — a mTLS config built with
    it rejects every peer. There is deliberately no implicit "trust everyone
    in the bundle set" fallback, because that is exactly the hole this class
    exists to close.
    """

    __slots__ = ("_rules",)

    def __init__(self) -> None:
        """Create an empty matcher that rejects every peer until rules are added."""
        self._rules: List[object] = []

    def allow_trust_domain(self, trust_domain: TrustDomain | str) -> "SpiffeIdMatcher":
        """
        Allow any SPIFFE ID in ``trust_domain`` regardless of path — the way to
        admit a whole federated trust domain (e.g. a customer's own SPIRE)
        rather than one workload. Returns ``self`` for chaining.
        """
        td = trust_domain if isinstance(trust_domain, TrustDomain) else TrustDomain(trust_domain)
        self._rules.append(_AnyPath(td))
        return self

    def allow_path_prefix(
        self, trust_domain: TrustDomain | str, prefix: str
    ) -> "SpiffeIdMatcher":
        """
        Allow SPIFFE IDs in ``trust_domain`` whose path starts with ``prefix``
        (normalized to a leading ``/``; matched on whole path segments).
        Returns ``self`` for chaining.
        """
        td = trust_domain if isinstance(trust_domain, TrustDomain) else TrustDomain(trust_domain)
        if not prefix.startswith("/"):
            prefix = "/" + prefix
        self._rules.append(_PathPrefix(td, prefix))
        return self

    def allow_exact(self, spiffe_id: SpiffeId | str) -> "SpiffeIdMatcher":
        """Allow exactly this one SPIFFE ID. Returns ``self`` for chaining."""
        sid = spiffe_id if isinstance(spiffe_id, SpiffeId) else SpiffeId.parse(spiffe_id)
        self._rules.append(_Exact(sid))
        return self

    def matches(self, spiffe_id: SpiffeId | str) -> bool:
        """Return ``True`` if ``spiffe_id`` satisfies at least one configured rule."""
        sid = spiffe_id if isinstance(spiffe_id, SpiffeId) else SpiffeId.parse(spiffe_id)
        return any(rule.matches(sid) for rule in self._rules)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Workload API material + source abstraction (mockable for tests)
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class X509Svid:
    """A workload's X.509-SVID: its SPIFFE ID plus the PEM cert chain and key."""

    spiffe_id: SpiffeId
    cert_chain_pem: bytes
    private_key_pem: bytes


@dataclass(slots=True)
class TrustBundleSet:
    """
    Trust bundles keyed by trust-domain name (PEM CA material). May span more
    than one trust domain — see :class:`SpiffeIdMatcher` for why federation
    means a peer's anchor can live outside ``penguintech.io``.
    """

    bundles: Dict[str, bytes] = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Whether the set carries no trust authorities at all."""
        return not self.bundles


@dataclass(slots=True)
class X509Context:
    """One attestation's result: the default SVID (if any) and its trust bundle set."""

    default_svid: Optional[X509Svid]
    bundles: TrustBundleSet


@dataclass(slots=True)
class JwtSvid:
    """A JWT-SVID: the signed token, its SPIFFE ID, and the audience it is scoped to."""

    token: str
    spiffe_id: SpiffeId
    audience: Tuple[str, ...]


class WorkloadApiSource(ABC):
    """
    The subset of SPIFFE Workload API behavior :class:`IdentityProvider`
    depends on, factored out as an interface so tests substitute a fake source
    instead of requiring a live SPIRE agent socket.
    """

    @abstractmethod
    def fetch_x509_context(self) -> X509Context:
        """Fetch the workload's current X.509-SVID(s) and trust bundle set."""

    @abstractmethod
    def fetch_jwt_svid(self, audience: str) -> JwtSvid:
        """Fetch a JWT-SVID scoped to ``audience`` for the workload's default identity."""


class RealWorkloadApiSource(WorkloadApiSource):
    """
    Production adapter backed by a live connection to the SPIFFE Workload API
    (typically a SPIRE agent Unix socket named by ``SPIFFE_ENDPOINT_SOCKET``).
    Deliberately thin — every decision this module makes lives elsewhere and
    is unit-tested against a fake source.
    """

    def __init__(self, socket_path: str) -> None:
        """Hold the resolved Workload API socket path; the SDK client is created lazily."""
        self._socket_path = socket_path

    @classmethod
    def connect_env(cls) -> "RealWorkloadApiSource":
        """Connect using the endpoint named by ``SPIFFE_ENDPOINT_SOCKET``, or raise if unset."""
        socket = os.environ.get(SPIFFE_ENDPOINT_SOCKET_ENV)
        if not socket:
            raise WorkloadApiUnavailable(
                f"{SPIFFE_ENDPOINT_SOCKET_ENV} is not set; no Workload API endpoint to attest to"
            )
        return cls(socket)

    def fetch_x509_context(self) -> X509Context:
        """Fetch the X.509 context from the live Workload API."""
        # TODO(spiffe-sdk): wire py-spiffe once it is a dependency, e.g.
        #   from spiffe import WorkloadApiClient
        #   client = WorkloadApiClient(spiffe_socket_path=self._socket_path)
        #   ctx = client.fetch_x509_context()
        # then map ctx.default_svid()/ctx.x509_bundle_set() into X509Context.
        # Until then, refuse loudly rather than pretend to have an identity.
        raise WorkloadApiUnavailable(
            "py-spiffe SDK not wired (TODO); RealWorkloadApiSource cannot attest yet"
        )

    def fetch_jwt_svid(self, audience: str) -> JwtSvid:
        """Fetch a JWT-SVID scoped to ``audience`` from the live Workload API."""
        # TODO(spiffe-sdk): client.fetch_jwt_svid(audiences={audience}).
        raise WorkloadApiUnavailable(
            "py-spiffe SDK not wired (TODO); RealWorkloadApiSource cannot fetch JWT-SVIDs yet"
        )


# ---------------------------------------------------------------------------
# mTLS config material
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class MtlsConfig:
    """
    mTLS configuration material for one side of a connection: this workload's
    SVID, the trust bundles that validate the peer's chain, and the allowlist
    that decides whether an already-trusted peer is *permitted*.

    Chain-of-trust validation (does the peer's cert chain to a bundle we hold)
    is the TLS stack's job and a separate, prior step; :meth:`authorize_peer`
    is the second gate — enforcing the :class:`SpiffeIdMatcher` against the
    peer's SPIFFE ID once the chain is trusted.
    """

    svid: X509Svid
    bundles: TrustBundleSet
    matcher: SpiffeIdMatcher
    is_server: bool

    def authorize_peer(self, peer_spiffe_id: SpiffeId | str | None) -> None:
        """
        Enforce the allowlist against an already-chain-validated peer's SPIFFE
        ID. A peer that presented no SVID (``None``) is rejected outright;
        otherwise :class:`PeerNotAuthorized` is raised unless the matcher admits
        the ID. This is the check that catches a missing/too-broad allowlist.
        """
        if peer_spiffe_id is None:
            raise PeerNotAuthorized("peer presented no SVID")
        try:
            sid = (
                peer_spiffe_id
                if isinstance(peer_spiffe_id, SpiffeId)
                else SpiffeId.parse(peer_spiffe_id)
            )
        except SpiffeIdError as exc:
            raise PeerNotAuthorized(f"peer presented an unparseable SVID: {exc}") from exc
        if not self.matcher.matches(sid):
            raise PeerNotAuthorized(f"peer SPIFFE ID {sid} is not permitted by policy")


# ---------------------------------------------------------------------------
# IdentityProvider
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class _IdentityState:
    """One attestation's held material: the current SVID and its trust bundle set."""

    svid: X509Svid
    bundles: TrustBundleSet


def is_production() -> bool:
    """
    House fail-safe posture check, mirroring ``skauswatch_auth::is_production``:
    production unless ``RELEASE_MODE`` is explicitly ``"false"``. When
    ``RELEASE_MODE`` is unset, an explicit dev/local/test environment name
    downgrades to non-production; anything else defaults to production so a
    misconfigured deploy fails closed rather than running without identity.
    """
    release_mode = os.environ.get("RELEASE_MODE")
    if release_mode is not None:
        return release_mode.strip().lower() != "false"
    env = (
        os.environ.get("WADDLEBOT_ENV")
        or os.environ.get("ENVIRONMENT")
        or os.environ.get("NODE_ENV")
        or ""
    ).strip().lower()
    return env not in {"development", "dev", "local", "test", "testing"}


class IdentityProvider:
    """
    SPIFFE Workload API client for one workload: attests to the local socket,
    holds the current X.509-SVID and trust bundle set, and builds mTLS
    :class:`MtlsConfig` material and JWT-SVIDs from them.

    Fail-safe policy (see module docs): in production a required identity that
    cannot be obtained hard-fails (:class:`WorkloadApiUnavailable`); anywhere
    else it degrades with a WARN and proceeds with no identity, so every
    method that needs one raises :class:`Degraded`. There is deliberately no
    deployment-domain bypass — a domain-based bypass is for license/feature
    gating only and must never exempt identity.
    """

    __slots__ = ("_source", "_state")

    def __init__(
        self,
        source: Optional[WorkloadApiSource],
        state: Optional[_IdentityState],
    ) -> None:
        """Hold the (optional) Workload API source and (optional) attested state."""
        self._source = source
        self._state = state

    @classmethod
    def connect(
        cls,
        *,
        source: Optional[WorkloadApiSource] = None,
        require: Optional[bool] = None,
    ) -> "IdentityProvider":
        """
        Attest to the Workload API and hold the resulting identity, applying the
        fail-safe policy. ``source`` may be injected (tests); otherwise a
        :class:`RealWorkloadApiSource` is built from ``SPIFFE_ENDPOINT_SOCKET``.
        ``require`` forces production posture on/off; when ``None`` it is
        resolved from the environment via :func:`is_production`.
        """
        prod = is_production() if require is None else require
        try:
            src = source if source is not None else RealWorkloadApiSource.connect_env()
            state = _attest(src)
        except Exception as exc:  # noqa: BLE001 - normalize any SDK/attestation error
            if prod:
                raise WorkloadApiUnavailable(
                    f"SPIFFE Workload API unreachable and identity is mandatory in production: {exc}"
                ) from exc
            logger.warning(
                "SPIFFE Workload API unavailable (%s); running WITHOUT workload identity (dev mode)",
                exc,
            )
            return cls(source=None, state=None)
        return cls(source=src, state=state)

    def refresh(self) -> None:
        """
        Re-attest and replace the held identity. In production a failed refresh
        raises but preserves the prior identity; outside production it degrades
        with a WARN without clearing a previously-held identity.
        """
        if self._source is None:
            raise Degraded("cannot refresh: provider is running without a Workload API source")
        try:
            self._state = _attest(self._source)
        except Exception as exc:  # noqa: BLE001 - normalize any SDK/attestation error
            if is_production():
                raise WorkloadApiUnavailable(f"refresh failed in production: {exc}") from exc
            logger.warning("SPIFFE refresh failed (%s); keeping prior identity", exc)

    def has_identity(self) -> bool:
        """Whether a workload identity is currently held (``False`` while degraded)."""
        return self._state is not None

    def spiffe_id(self) -> SpiffeId:
        """Return this workload's own SPIFFE ID, or raise :class:`Degraded` if none is held."""
        if self._state is None:
            raise Degraded("no workload identity held")
        return self._state.svid.spiffe_id

    def fetch_jwt_svid(self, audience: str) -> JwtSvid:
        """
        Fetch a JWT-SVID scoped to ``audience``. Note: a JWT-SVID is not the
        inter-service machine JWT required by ``security.md`` — that remains a
        separate, mandatory gate on every call regardless of transport.
        """
        if self._source is None or self._state is None:
            raise Degraded("cannot fetch JWT-SVID while running without a workload identity")
        try:
            return self._source.fetch_jwt_svid(audience)
        except IdentityError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalize SDK errors
            raise JwtSvidError(f"failed to fetch JWT-SVID: {exc}") from exc

    def server_tls_config(self, allowed: SpiffeIdMatcher) -> MtlsConfig:
        """
        Build server-side mTLS material that will require every connecting peer
        to present a chain-valid SVID whose ID ``allowed`` admits. Raises
        :class:`Degraded` if no identity is held, :class:`EmptyTrustBundle` if
        no peer could ever be validated.
        """
        return self._tls_config(allowed, is_server=True)

    def client_tls_config(self, allowed: SpiffeIdMatcher) -> MtlsConfig:
        """
        Build client-side mTLS material that will require the server to present
        a chain-valid SVID whose ID ``allowed`` admits. Same failure modes as
        :meth:`server_tls_config`.
        """
        return self._tls_config(allowed, is_server=False)

    def _tls_config(self, allowed: SpiffeIdMatcher, *, is_server: bool) -> MtlsConfig:
        """Shared guard + construction for the server/client TLS config builders."""
        if self._state is None:
            raise Degraded("cannot build a mTLS config while running without a workload identity")
        if self._state.bundles.is_empty():
            raise EmptyTrustBundle(
                "trust bundle set has no authorities; refusing to build a mTLS config that trusts nothing"
            )
        return MtlsConfig(
            svid=self._state.svid,
            bundles=self._state.bundles,
            matcher=allowed,
            is_server=is_server,
        )


def _attest(source: WorkloadApiSource) -> _IdentityState:
    """
    Fetch the current X.509 context from ``source`` and extract the default SVID
    and bundle set, or raise :class:`NoDefaultSvid` if the API issued none.
    """
    ctx = source.fetch_x509_context()
    if ctx.default_svid is None:
        raise NoDefaultSvid("SPIFFE Workload API returned no X.509-SVID for this workload")
    return _IdentityState(svid=ctx.default_svid, bundles=ctx.bundles)
