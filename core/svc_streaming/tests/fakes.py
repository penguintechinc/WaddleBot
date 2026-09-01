"""Test doubles -- a fake ffmpeg subprocess (never a real `ffmpeg` exec) and a fake token debit.

`FFmpegSupervisor` is real; only the OS-level `subprocess_exec` call it
makes is substituted, per this PR's task description ("MOCK the ffmpeg
subprocess... do NOT spawn real ffmpeg in unit tests"). `FakeProcess`
mimics the subset of `asyncio.subprocess.Process`'s interface
`FFmpegSupervisor` actually calls.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any


class FakeProcess:
    """A fake `asyncio.subprocess.Process` -- tracks signals sent, never spawns a real process."""

    _next_pid = 10000

    def __init__(self, args: tuple[Any, ...]) -> None:
        """Assign a deterministic, incrementing fake PID."""
        self.args = args
        self.pid = FakeProcess._next_pid
        FakeProcess._next_pid += 1
        self.returncode: int | None = None
        self.signals_received: list[int] = []
        self._exit_event = asyncio.Event()

    def send_signal(self, sig: int) -> None:
        """Record the signal; a real ffmpeg would exit on SIGTERM/SIGKILL -- simulate that."""
        self.signals_received.append(sig)
        self.returncode = 0
        self._exit_event.set()

    def kill(self) -> None:
        """Simulate a hard kill -- always sets returncode immediately."""
        self.returncode = -9
        self._exit_event.set()

    async def wait(self) -> int:
        """Block until `send_signal`/`kill` has set `returncode`."""
        await self._exit_event.wait()
        assert self.returncode is not None  # noqa: S101 - test double invariant
        return self.returncode


@dataclass(slots=True)
class FakeSubprocessExec:
    """Callable matching `asyncio.create_subprocess_exec`'s signature; records every call."""

    processes: list[FakeProcess] = field(default_factory=list)
    calls: list[tuple[Any, ...]] = field(default_factory=list)

    async def __call__(self, *args: Any, **kwargs: Any) -> FakeProcess:
        """Return a new `FakeProcess` instead of exec'ing anything real."""
        self.calls.append(args)
        process = FakeProcess(args)
        self.processes.append(process)
        return process
