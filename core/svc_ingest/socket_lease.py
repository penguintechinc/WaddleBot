"""Valkey-lease-based socket ownership.

Exactly one live svc-ingest replica holds each `(provider, community)`
persistent-socket lease at a time. svc-ingest scales horizontally
(multiple replicas, `pipeline.svcIngest.replicas` in Helm), but a
gateway-socket receiver (`receivers/discord_gateway.py`) is a
PLATFORM-level, stateful connection -- N replicas
each independently starting the same Discord bot connection would mean N
duplicate gateway sessions on one bot token (Discord will start closing/
rate-limiting the older ones) and, worse, N-fold duplicate fan-out of every
inbound event. Confirmed design: at most one socket per `(provider,
community)`, so sockets are assignable via a lease rather than requiring
leader election over the whole replica set.

Lease key: `waddles:socket-owner:{provider}:{community}` -> the claiming
replica's `owner_id`, with a TTL (`SET ... NX PX ttl_ms`, atomic claim --
first replica to ask wins, no election round). A replica renews on
`renew_interval_s` (comfortably below the TTL) via a compare-and-expire
Lua script so a replica that lost its lease (TTL lapsed, e.g. it was
paused/GC'd) can never accidentally re-extend someone else's claim.
Release on clean shutdown is compare-and-delete for the same reason. No
rebalancing of an ALREADY-held lease when a new replica joins -- it only
claims what is unheld or expired, matching "assignable, not elected".

`PLATFORM_COMMUNITY` is the sentinel `community` value for a provider like
Discord that has no real per-community socket at all (one bot token, one
gateway connection, serving every guild/community it has been invited to)
-- the same generic `(provider, community)` lease shape applies without a
second key scheme for platform-wide providers.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Awaitable
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)

DEFAULT_LEASE_TTL_S = 30.0
DEFAULT_RENEW_INTERVAL_S = 10.0

#: Sentinel `community` for a provider with one platform-wide socket
#: rather than a real per-community one (see module docstring).
PLATFORM_COMMUNITY = "_platform"

# Compare-and-expire / compare-and-delete: both must verify the caller
# still holds the lease (GET == our own owner_id) before mutating it --
# otherwise a replica whose TTL already lapsed could renew or delete a
# DIFFERENT replica's now-current claim on the same key.
_RENEW_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("PEXPIRE", KEYS[1], ARGV[2])
else
    return 0
end
"""

_RELEASE_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


class LeaseRedisLike(Protocol):
    """The Valkey methods `SocketLease` needs -- narrow on purpose, easy to fake in tests.

    Declared non-`async def`/`Awaitable[Any]`-returning + positional-only
    params (`/`) so `redis.asyncio.Redis` (whose real `set`/`eval` stubs
    return `Awaitable[...]` from a non-`async def`-shaped signature, plus
    extra optional params this Protocol doesn't need) still structurally
    satisfies this Protocol -- a plain `async def` here would synthesize a
    `Coroutine[Any, Any, Any]` return type, which real redis-py's broader
    `Awaitable[...]` return does NOT covariantly satisfy.
    """

    def set(
        self, name: str, value: str, /, *, nx: bool = False, px: int | None = None
    ) -> Awaitable[Any]:
        """SET with optional NX (claim-only-if-absent) / PX (TTL in ms)."""
        ...

    def eval(self, script: str, numkeys: int, /, *keys_and_args: str) -> Awaitable[Any]:
        """Redis `EVAL` -- runs a Lua script server-side, NOT Python's `eval()`.

        No untrusted input ever reaches this -- `script` is always one of
        this module's own two constants below, used for the
        compare-and-expire/compare-and-delete ops.
        """
        ...


def lease_key(provider: str, community: str) -> str:
    """Build the `waddles:socket-owner:{provider}:{community}` lease key."""
    return f"waddles:socket-owner:{provider}:{community}"


@dataclass(slots=True)
class SocketLease:
    """One `(provider, community)` lease, claimed/renewed/released by `owner_id`."""

    provider: str
    community: str
    owner_id: str
    redis_client: LeaseRedisLike
    ttl_s: float = DEFAULT_LEASE_TTL_S

    @property
    def key(self) -> str:
        """The Valkey key this lease lives at."""
        return lease_key(self.provider, self.community)

    async def try_claim(self) -> bool:
        """Atomically claim the lease iff unheld or expired. True iff WE now hold it."""
        acquired = await self.redis_client.set(
            self.key, self.owner_id, nx=True, px=int(self.ttl_s * 1000)
        )
        return bool(acquired)

    async def renew(self) -> bool:
        """Extend the TTL iff we still hold it. False means we lost it -- caller must stop."""
        result = await self.redis_client.eval(
            _RENEW_SCRIPT, 1, self.key, self.owner_id, str(int(self.ttl_s * 1000))
        )
        return bool(result)

    async def release(self) -> None:
        """Best-effort release -- only deletes the key if we still own it (compare-and-delete)."""
        await self.redis_client.eval(_RELEASE_SCRIPT, 1, self.key, self.owner_id)


class LeasedSocketReceiver(Protocol):
    """The receiver shape `LeasedReceiver` wraps -- matches `DiscordGatewayReceiver`'s own."""

    async def run(self) -> None:
        """Connect and run until the connection ends or `stop()` is called."""
        ...

    async def stop(self) -> None:
        """Close the connection. Never raises."""
        ...


@dataclass(slots=True)
class LeasedReceiver:
    """Wraps a socket receiver so it only runs while this replica holds its `SocketLease`.

    `run()` is the `coro_factory` registered with `ReceiverSupervisor`
    (`supervisor.py`) -- it does NOT raise when the lease can't be claimed
    or is later lost; it simply returns, and `ReceiverSupervisor`'s own
    restart-on-exit + backoff loop retries claiming later with no separate
    machinery needed (a lost/unclaimed lease and a died receiver are the
    same "try again later" shape from the supervisor's point of view).
    """

    receiver: LeasedSocketReceiver
    redis_client: LeaseRedisLike
    provider: str
    community: str
    owner_id: str
    ttl_s: float = DEFAULT_LEASE_TTL_S
    renew_interval_s: float = DEFAULT_RENEW_INTERVAL_S
    _sleep: Any = field(default=asyncio.sleep, repr=False)

    def _build_lease(self) -> SocketLease:
        return SocketLease(
            provider=self.provider,
            community=self.community,
            owner_id=self.owner_id,
            redis_client=self.redis_client,
            ttl_s=self.ttl_s,
        )

    async def run(self) -> None:
        """Claim the lease; if claimed, run the receiver until it exits or the lease is lost."""
        lease = self._build_lease()
        if not await lease.try_claim():
            logger.info(
                "socket_lease.not_claimed provider=%s community=%s owner=%s",
                self.provider,
                self.community,
                self.owner_id,
            )
            return

        logger.info(
            "socket_lease.claimed provider=%s community=%s owner=%s",
            self.provider,
            self.community,
            self.owner_id,
        )
        renew_task = asyncio.ensure_future(self._renew_loop(lease))
        try:
            await self.receiver.run()
        except asyncio.CancelledError:
            await self.receiver.stop()
            raise
        finally:
            renew_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await renew_task
            await lease.release()
            logger.info(
                "socket_lease.released provider=%s community=%s owner=%s",
                self.provider,
                self.community,
                self.owner_id,
            )

    async def _renew_loop(self, lease: SocketLease) -> None:
        """Renew on `renew_interval_s`; force the receiver to stop the moment we lose the lease."""
        while True:
            await self._sleep(self.renew_interval_s)
            if not await lease.renew():
                logger.warning(
                    "socket_lease.lost provider=%s community=%s owner=%s",
                    self.provider,
                    self.community,
                    self.owner_id,
                )
                await self.receiver.stop()
                return
