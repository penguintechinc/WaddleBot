"""ReceiverSupervisor -- restart-on-exit + exponential backoff for long-lived receiver tasks.

svc-gateway's whole job is holding PERSISTENT inbound sockets (a Discord
bot gateway connection today, more platforms later) as long-lived asyncio
tasks. A raw `asyncio.ensure_future(receiver.run())` (the pattern
`core/svc_ingest/app.py` uses for its own, much shorter-lived poll loop)
dies silently on any unhandled exception -- the task just stops, no retry,
no restart, no crash loud enough for anyone to notice, and the platform
quietly loses that entire receiver's traffic. `ReceiverSupervisor` wraps
each registered receiver coroutine in its own supervised loop so a dropped
gateway connection, an auth failure, or any other unhandled exception
restarts the receiver rather than ending it -- backoff shape (double on
failure, cap at `max_backoff_s`, reset to `base_backoff_s` on a clean
`RECEIVER_HEALTHY_S`-long run) deliberately mirrors
`flask_core.stage_runner.BundlePoller.poll_once` (stage_runner.py:185-211)
so the two "keep retrying, never go idle, never hammer" policies in this
codebase read the same way.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

#: Same defaults `flask_core.stage_runner` uses for its own backoff bounds.
DEFAULT_BASE_BACKOFF_S = 1.0
DEFAULT_MAX_BACKOFF_S = 60.0

#: A receiver run that stays up at least this long before dying is treated
#: as "was healthy" -- its next restart starts from `base_backoff_s` again
#: rather than continuing to double from wherever a much-earlier failure
#: streak left off. Without this, one receiver that has ever failed twice
#: stays capped at a slow backoff forever, even after running cleanly for
#: hours in between.
_HEALTHY_RUN_S = 30.0

#: Injected in tests to make `_HEALTHY_RUN_S`/backoff waits instant --
#: production code always uses the real `asyncio.sleep`/`time.monotonic`.
_SleepFn = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class _Supervised:
    """One registered receiver's supervision state."""

    name: str
    coro_factory: Callable[[], Awaitable[None]]
    task: asyncio.Task[None] | None = None
    restart_count: int = 0


@dataclass(slots=True)
class ReceiverSupervisor:
    """Runs registered receiver coroutines as supervised, restart-on-exit asyncio tasks.

    `register()` before `start()`; each registered receiver gets its own
    independent supervised task -- one receiver crashing/restarting never
    affects another's. `stop()` cancels every supervised task and awaits
    them, swallowing the resulting `CancelledError` (that cancellation is
    this supervisor's own shutdown signal, not a failure).
    """

    base_backoff_s: float = DEFAULT_BASE_BACKOFF_S
    max_backoff_s: float = DEFAULT_MAX_BACKOFF_S
    _sleep: _SleepFn = field(default=asyncio.sleep, repr=False)
    _receivers: dict[str, _Supervised] = field(default_factory=dict)
    _running: bool = False

    def register(self, name: str, coro_factory: Callable[[], Awaitable[None]]) -> None:
        """Register a receiver by name. `coro_factory()` is called fresh on every (re)start."""
        if name in self._receivers:
            raise ValueError(f"receiver {name!r} already registered")
        self._receivers[name] = _Supervised(name=name, coro_factory=coro_factory)

    def restart_count(self, name: str) -> int:
        """How many times the named receiver has been restarted after a failed/exited run."""
        return self._receivers[name].restart_count

    async def start(self) -> None:
        """Start a supervised task for every registered receiver. Idempotent per receiver."""
        self._running = True
        for supervised in self._receivers.values():
            if supervised.task is None:
                supervised.task = asyncio.ensure_future(self._supervise(supervised))

    async def stop(self) -> None:
        """Cancel and await every supervised task. Never raises -- shutdown must not fail."""
        self._running = False
        tasks = [s.task for s in self._receivers.values() if s.task is not None]
        for task in tasks:
            task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass  # expected -- our own cancel() above, not a receiver failure
            except Exception as exc:  # noqa: BLE001 - shutdown must not raise
                logger.warning("supervisor.stop_error error=%s", exc)
        for supervised in self._receivers.values():
            supervised.task = None

    async def _supervise(self, supervised: _Supervised) -> None:
        """One receiver's restart-on-exit + exponential-backoff loop. Never raises out."""
        backoff_s = self.base_backoff_s
        while self._running:
            started_at = time.monotonic()
            try:
                await supervised.coro_factory()
                # A receiver coroutine returning normally is ALSO "died" --
                # a persistent-socket receiver's contract is to run forever
                # until cancelled; returning means its connection ended
                # (or it was never opened), so it restarts exactly like a
                # raised exception would.
                logger.warning(
                    "supervisor.receiver_exited name=%s -- restarting", supervised.name
                )
            except asyncio.CancelledError:
                raise  # our own stop() -- propagate, do not restart
            except Exception as exc:  # noqa: BLE001 - one receiver's bug must never kill others
                logger.error(
                    "supervisor.receiver_failed name=%s error=%s backoff_s=%s",
                    supervised.name,
                    exc,
                    backoff_s,
                )

            if not self._running:
                return

            ran_for_s = time.monotonic() - started_at
            supervised.restart_count += 1
            if ran_for_s >= _HEALTHY_RUN_S:
                backoff_s = self.base_backoff_s
            await self._sleep(backoff_s)
            backoff_s = min(backoff_s * 2, self.max_backoff_s)
