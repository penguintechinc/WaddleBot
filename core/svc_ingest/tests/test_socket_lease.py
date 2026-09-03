"""Tests for `socket_lease` -- Valkey-lease-based socket ownership (claim/renew/failover).

`redis_client` is a real `fakeredis.FakeAsyncRedis` -- genuine `SET NX PX`
and Lua `EVAL` semantics (fakeredis's Lua support needs the `lupa`
extra, test-only -- real Valkey supports `EVAL` natively), not a mocked
call, matching this container's own `test_runner.py`/`test_fanout.py`
precedent. Fail-first: swapping `SocketLease.renew`'s compare-and-expire
script for an unconditional `PEXPIRE` turns `test_replica_b_cannot_renew_
replica_as_lease` green-for-the-wrong-reason into a false negative
(replica B would keep the lease alive forever) -- confirmed, reverted.
"""

from __future__ import annotations

import asyncio
from typing import Any

from socket_lease import (
    PLATFORM_COMMUNITY,
    LeasedReceiver,
    SocketLease,
    lease_key,
)

PROVIDER = "discord"


class _FakeReceiver:
    """Minimal `LeasedSocketReceiver` double -- `run()` blocks until `stop()` is called."""

    def __init__(self) -> None:
        self.run_calls = 0
        self.stop_calls = 0
        self._stop_event = asyncio.Event()

    async def run(self) -> None:
        self.run_calls += 1
        await self._stop_event.wait()

    async def stop(self) -> None:
        self.stop_calls += 1
        self._stop_event.set()


class TestLeaseKey:
    def test_key_shape(self) -> None:
        assert lease_key("discord", "_platform") == "waddles:socket-owner:discord:_platform"


class TestClaimRenewRelease:
    async def test_claim_succeeds_when_unheld(self, redis_client: Any) -> None:
        lease = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        assert await lease.try_claim() is True

    async def test_second_replica_cannot_claim_a_held_lease(self, redis_client: Any) -> None:
        lease_a = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        lease_b = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
            redis_client=redis_client,
        )
        assert await lease_a.try_claim() is True
        assert await lease_b.try_claim() is False

    async def test_owner_can_renew_its_own_lease(self, redis_client: Any) -> None:
        lease = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        assert await lease.try_claim() is True
        assert await lease.renew() is True

    async def test_non_owner_cannot_renew_another_replicas_lease(self, redis_client: Any) -> None:
        lease_a = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        lease_b = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
            redis_client=redis_client,
        )
        assert await lease_a.try_claim() is True
        # replica-b never held the lease -- its renew must be a no-op, not
        # a forged extension of replica-a's claim.
        assert await lease_b.renew() is False

    async def test_release_frees_the_lease_for_another_claimant(self, redis_client: Any) -> None:
        lease_a = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        lease_b = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
            redis_client=redis_client,
        )
        assert await lease_a.try_claim() is True
        await lease_a.release()
        assert await lease_b.try_claim() is True

    async def test_non_owner_release_is_a_noop(self, redis_client: Any) -> None:
        """Compare-and-delete: releasing a lease you don't own must not free someone else's."""
        lease_a = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        lease_b = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
            redis_client=redis_client,
        )
        assert await lease_a.try_claim() is True
        await lease_b.release()  # replica-b never held it -- must be a no-op
        assert await lease_b.try_claim() is False  # still held by replica-a


class TestLeasedReceiver:
    async def test_run_starts_receiver_when_lease_claimed(self, redis_client: Any) -> None:
        receiver = _FakeReceiver()
        leased = LeasedReceiver(
            receiver=receiver,
            redis_client=redis_client,
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
        )
        task = asyncio.ensure_future(leased.run())
        await asyncio.sleep(0.05)
        assert receiver.run_calls == 1

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def test_run_returns_immediately_when_lease_already_held(self, redis_client: Any) -> None:
        """A replica that loses the claim race never starts its receiver.

        The raw `run()` coroutine just returns, letting
        `ReceiverSupervisor`'s own backoff retry later.
        """
        other = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            redis_client=redis_client,
        )
        assert await other.try_claim() is True

        receiver = _FakeReceiver()
        leased = LeasedReceiver(
            receiver=receiver,
            redis_client=redis_client,
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
        )
        await leased.run()  # returns without hanging -- lease unavailable
        assert receiver.run_calls == 0

    async def test_losing_the_lease_stops_the_receiver(self, redis_client: Any) -> None:
        """Fail-first proof of failover.

        Replica A's lease is stolen (simulated expiry via a direct
        compare-and-delete + replica B's claim); A's renew loop must
        notice and force its receiver to stop.
        """
        receiver = _FakeReceiver()
        leased_a = LeasedReceiver(
            receiver=receiver,
            redis_client=redis_client,
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
            renew_interval_s=0.01,
        )
        task = asyncio.ensure_future(leased_a.run())
        await asyncio.sleep(0.03)
        assert receiver.run_calls == 1

        # Simulate the lease expiring and replica-b claiming it (a real TTL
        # lapse in production; forced here via direct key deletion + a
        # fresh claim so the test doesn't wait out a real TTL).
        await redis_client.delete(lease_key(PROVIDER, PLATFORM_COMMUNITY))
        other = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
            redis_client=redis_client,
        )
        assert await other.try_claim() is True

        # replica-a's renew loop should notice on its next tick and stop
        # its receiver -- `run()` then returns.
        await asyncio.wait_for(task, timeout=2.0)
        assert receiver.stop_calls >= 1

    async def test_cancellation_stops_receiver_and_releases_lease(self, redis_client: Any) -> None:
        receiver = _FakeReceiver()
        leased = LeasedReceiver(
            receiver=receiver,
            redis_client=redis_client,
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-a",
        )
        task = asyncio.ensure_future(leased.run())
        await asyncio.sleep(0.03)
        assert receiver.run_calls == 1

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert receiver.stop_calls >= 1
        # Lease released -- another replica can now claim it.
        other = SocketLease(
            provider=PROVIDER,
            community=PLATFORM_COMMUNITY,
            owner_id="replica-b",
            redis_client=redis_client,
        )
        assert await other.try_claim() is True
