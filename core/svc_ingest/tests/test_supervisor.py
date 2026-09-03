"""Tests for `supervisor.ReceiverSupervisor` -- restart-on-exit + exponential backoff.

`_sleep` injection (a fake that records requested delays and returns
instantly) keeps these tests fast/deterministic without a real
`asyncio.sleep` -- production code always uses the real one (the
dataclass field's own default). Fail-first: temporarily removing the
`except Exception` branch's restart path (falling straight through to a
bare re-raise) turns `test_raising_receiver_is_restarted` red instead of
green -- confirmed, reverted.
"""

from __future__ import annotations

import asyncio

from supervisor import ReceiverSupervisor


class _FakeSleep:
    """Records requested backoff durations, returns instantly -- keeps tests fast."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, delay: float) -> None:
        self.calls.append(delay)


class TestRestartOnFailure:
    async def test_raising_receiver_is_restarted(self) -> None:
        attempts = 0
        done = asyncio.Event()

        async def flaky() -> None:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise RuntimeError("boom")
            done.set()
            await asyncio.sleep(100)  # block "running" until stop() cancels us

        supervisor = ReceiverSupervisor(base_backoff_s=0.01, max_backoff_s=0.05)
        supervisor._sleep = _FakeSleep()  # noqa: SLF001 - test override, no public setter
        supervisor.register("flaky", flaky)
        await supervisor.start()
        await asyncio.wait_for(done.wait(), timeout=2.0)
        await supervisor.stop()

        assert attempts == 3
        assert supervisor.restart_count("flaky") == 2  # two failed attempts before success

    async def test_returning_receiver_is_also_restarted(self) -> None:
        """A receiver coroutine that returns normally (not just raises) is treated as died.

        A persistent-socket receiver's contract is "run forever until
        cancelled" -- returning early (connection dropped, auth ended,
        whatever) is exactly as much a failure as raising.
        """
        attempts = 0
        done = asyncio.Event()

        async def exits_cleanly() -> None:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                return
            done.set()
            await asyncio.sleep(100)

        supervisor = ReceiverSupervisor(base_backoff_s=0.01, max_backoff_s=0.05)
        supervisor._sleep = _FakeSleep()  # noqa: SLF001
        supervisor.register("exits_cleanly", exits_cleanly)
        await supervisor.start()
        await asyncio.wait_for(done.wait(), timeout=2.0)
        await supervisor.stop()

        assert attempts == 2
        assert supervisor.restart_count("exits_cleanly") == 1

    async def test_backoff_doubles_and_caps_at_max(self) -> None:
        attempts = 0
        done = asyncio.Event()

        async def fails_four_times() -> None:
            nonlocal attempts
            attempts += 1
            if attempts < 5:
                raise RuntimeError("boom")
            done.set()
            await asyncio.sleep(100)

        sleep = _FakeSleep()
        supervisor = ReceiverSupervisor(base_backoff_s=1.0, max_backoff_s=3.0)
        supervisor._sleep = sleep  # noqa: SLF001
        supervisor.register("r", fails_four_times)
        await supervisor.start()
        await asyncio.wait_for(done.wait(), timeout=2.0)
        await supervisor.stop()

        # 1.0, 2.0, 3.0 (capped), 3.0 (capped) -- four failures before the
        # fifth attempt finally succeeds.
        assert sleep.calls == [1.0, 2.0, 3.0, 3.0]

    async def test_independent_receivers_do_not_affect_each_other(self) -> None:
        healthy_calls = 0
        flaky_attempts = 0
        flaky_done = asyncio.Event()

        async def healthy() -> None:
            nonlocal healthy_calls
            healthy_calls += 1
            await asyncio.sleep(100)

        async def flaky() -> None:
            nonlocal flaky_attempts
            flaky_attempts += 1
            if flaky_attempts < 3:
                raise RuntimeError("boom")
            flaky_done.set()
            await asyncio.sleep(100)

        supervisor = ReceiverSupervisor(base_backoff_s=0.01, max_backoff_s=0.05)
        supervisor._sleep = _FakeSleep()  # noqa: SLF001
        supervisor.register("healthy", healthy)
        supervisor.register("flaky", flaky)
        await supervisor.start()
        await asyncio.wait_for(flaky_done.wait(), timeout=2.0)
        await supervisor.stop()

        assert healthy_calls == 1  # never restarted -- it never died
        assert flaky_attempts == 3


class TestStop:
    async def test_stop_cancels_and_finishes_cleanly(self) -> None:
        started = asyncio.Event()

        async def long_lived() -> None:
            started.set()
            await asyncio.sleep(100)

        supervisor = ReceiverSupervisor()
        supervisor.register("long_lived", long_lived)
        await supervisor.start()
        await asyncio.wait_for(started.wait(), timeout=2.0)
        await asyncio.wait_for(supervisor.stop(), timeout=2.0)  # must not hang

    async def test_register_duplicate_name_raises(self) -> None:
        async def noop() -> None:
            await asyncio.sleep(100)

        supervisor = ReceiverSupervisor()
        supervisor.register("dup", noop)
        try:
            supervisor.register("dup", noop)
        except ValueError:
            pass
        else:
            raise AssertionError("expected ValueError for duplicate receiver name")
