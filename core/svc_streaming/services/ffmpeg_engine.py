"""The real media engine -- a genuine `ffmpeg` subprocess, not a simulated/stubbed one.

`build_ffmpeg_args()` is a pure function turning a stream's config +
enabled forward targets into the exact argv this process will exec --
tested by asserting the literal arg list for a given input, never by
inspecting a mocked call after the fact only loosely. `FFmpegSupervisor`
owns the actual subprocess lifecycle (start/stop/health) via
`asyncio.create_subprocess_exec` -- real process management (PID tracking,
SIGTERM-then-SIGKILL graceful stop, liveness poll), scoped to one
subprocess per community's active stream (in-memory registry; HA/
multi-replica leader-election is documented follow-up, `replicas: 1` in
`values.yaml`'s `pipeline.svcStreaming` for now).

Ingest model: `source_url` is a source this process PULLS from (`ffmpeg
-i <source_url>`) -- an existing upstream HLS playlist or RTMP relay --
not an RTMP listener this pod opens (no privileged port, no `hostNetwork`,
matches `security.md` K8s Network Security's "no NodePort/hostPort"
baseline and keeps this container's declared ports to control REST/gRPC
only, same as the landed scaffold). FORWARD fan-out uses one `-f flv`
output block per enabled target (`-c copy` passthrough, or per-output
`-c:v libx264`/`-c:a aac` when TRANSCODE is admitted) plus an optional
`-f mp4` recording output -- straightforward N-output ffmpeg syntax,
correct and testable; consolidating transcode fan-out onto the `tee`
muxer (one encode, N copies) instead of per-output re-encoding is a real
CPU-cost optimization deferred as follow-up, not a correctness gap.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: Grace period between SIGTERM and SIGKILL when stopping a running job --
#: lets ffmpeg flush its output muxers cleanly before a hard kill.
_STOP_GRACE_SECONDS = 5.0


@dataclass(slots=True, frozen=True)
class ForwardTargetSpec:
    """One enabled forward target -- the minimal shape `build_ffmpeg_args()` needs."""

    forward_url: str


@dataclass(slots=True, frozen=True)
class StreamJobSpec:
    """Everything `build_ffmpeg_args()` needs to build one job's argv."""

    source_url: str
    targets: list[ForwardTargetSpec]
    transcode: bool
    transcode_bitrate_kbps: int
    record_path: str | None


def build_ffmpeg_args(spec: StreamJobSpec, *, ffmpeg_binary: str = "ffmpeg") -> list[str]:
    """Build the real ffmpeg argv for one forward job -- pure, deterministic, unit-testable.

    `-re` paces the read at native frame rate (correct for a live-source
    pull, not a fast-as-possible file transcode); `-y` never prompts on an
    existing recording path. Raises `ValueError` if there is nothing to
    do (no enabled targets and no recording) -- callers must not spawn a
    no-op ffmpeg process.
    """
    if not spec.targets and not spec.record_path:
        raise ValueError("build_ffmpeg_args: at least one enabled target or recording is required")

    args: list[str] = [ffmpeg_binary, "-y", "-re", "-i", spec.source_url]

    if spec.transcode:
        codec_args = [
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            f"{spec.transcode_bitrate_kbps}k",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
        ]
    else:
        codec_args = ["-c", "copy"]

    for target in spec.targets:
        args += [*codec_args, "-f", "flv", target.forward_url]

    if spec.record_path:
        # Recording is always a lossless remux of the (possibly
        # transcoded) stream -- `-c copy` here means "don't re-encode a
        # third time for the recording", independent of whether the
        # forward outputs above were transcoded.
        args += ["-c", "copy", "-f", "mp4", spec.record_path]

    return args


@dataclass(slots=True)
class ManagedProcess:
    """A running ffmpeg job this process is supervising."""

    pid: int
    args: list[str] = field(repr=False)
    process: Any = field(repr=False)


class FFmpegSupervisor:
    """Owns the real subprocess lifecycle for every community's active forward job.

    `subprocess_exec` is injectable (defaults to `asyncio.create_subprocess_exec`)
    so unit tests substitute a fake coroutine instead of monkeypatching
    asyncio internals -- see `tests/test_ffmpeg_engine.py`. NEVER spawns a
    real `ffmpeg` process in the test suite; the real binary is only ever
    exec'd against a live source URL in an actual deployment.
    """

    def __init__(self, *, subprocess_exec: Any = None) -> None:
        """Build a supervisor; `subprocess_exec` defaults to the real asyncio primitive."""
        self._subprocess_exec = subprocess_exec or asyncio.create_subprocess_exec
        self._jobs: dict[int, ManagedProcess] = {}

    async def start(self, config_id: int, args: list[str]) -> ManagedProcess:
        """Exec `args` as a real subprocess, tracked under `config_id`.

        Raises `RuntimeError` if a job is already running for this
        `config_id` -- callers (the `stop` route, or a second `start`)
        must stop the existing job first, never silently orphan it.
        """
        if config_id in self._jobs:
            raise RuntimeError(f"a forward job is already running for config_id={config_id}")

        process = await self._subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        managed = ManagedProcess(pid=process.pid, args=args, process=process)
        self._jobs[config_id] = managed
        logger.info("ffmpeg_engine.started config_id=%s pid=%s", config_id, managed.pid)
        return managed

    def is_running(self, config_id: int) -> bool:
        """True if a job is tracked for `config_id` AND its process hasn't exited."""
        managed = self._jobs.get(config_id)
        if managed is None:
            return False
        return managed.process.returncode is None

    def get(self, config_id: int) -> ManagedProcess | None:
        """Return the tracked job for `config_id`, or `None`."""
        return self._jobs.get(config_id)

    async def stop(self, config_id: int, *, grace_seconds: float = _STOP_GRACE_SECONDS) -> None:
        """SIGTERM the job for `config_id`, escalating to SIGKILL after `grace_seconds`.

        A no-op (not an error) if no job is tracked -- `stop` is safe to
        call idempotently, matching every other lifecycle method in this
        service's blueprint layer.
        """
        managed = self._jobs.pop(config_id, None)
        if managed is None:
            return

        process = managed.process
        if process.returncode is not None:
            return  # already exited on its own

        process.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(process.wait(), timeout=grace_seconds)
        except TimeoutError:
            logger.warning(
                "ffmpeg_engine.force_kill config_id=%s pid=%s -- SIGTERM grace expired",
                config_id,
                managed.pid,
            )
            process.kill()
            await process.wait()
        logger.info("ffmpeg_engine.stopped config_id=%s pid=%s", config_id, managed.pid)

    async def stop_all(self) -> None:
        """Stop every tracked job -- called from the app's `after_serving` shutdown hook."""
        for config_id in list(self._jobs):
            await self.stop(config_id)


def ensure_recordings_dir(recordings_dir: str) -> None:
    """Create `recordings_dir` (and parents) if it doesn't exist yet -- real, not simulated I/O."""
    Path(recordings_dir).mkdir(parents=True, exist_ok=True)


def recording_path(recordings_dir: str, config_id: int, session_started_at: str) -> str:
    """Deterministic recording file path for one session -- no collisions across restarts."""
    safe_timestamp = session_started_at.replace(":", "-")
    return str(Path(recordings_dir) / f"community-{config_id}-{safe_timestamp}.mp4")
