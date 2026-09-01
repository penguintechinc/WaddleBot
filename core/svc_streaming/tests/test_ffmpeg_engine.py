"""Real ffmpeg argv construction + real subprocess lifecycle -- against a fake exec only.

`build_ffmpeg_args()` is asserted by exact argv, not loosely inspected --
this is the single most safety-critical function in this service (it's
what actually opens outbound network connections to caller-supplied
targets). `FFmpegSupervisor` tests use `tests.fakes.FakeSubprocessExec`
exclusively -- no real `ffmpeg` binary is ever invoked.
"""

from __future__ import annotations

import signal

import pytest

from services.ffmpeg_engine import (
    FFmpegSupervisor,
    ForwardTargetSpec,
    StreamJobSpec,
    build_ffmpeg_args,
    ensure_recordings_dir,
    recording_path,
)
from tests.fakes import FakeSubprocessExec


def test_build_args_passthrough_single_target() -> None:
    """No transcode, one target -- `-c copy` fan-out, exact argv."""
    spec = StreamJobSpec(
        source_url="rtmp://ingest.example.com/live/key",
        targets=[ForwardTargetSpec(forward_url="rtmp://twitch.example.com/live/tkey")],
        transcode=False,
        transcode_bitrate_kbps=4000,
        record_path=None,
    )
    args = build_ffmpeg_args(spec)
    assert args == [
        "ffmpeg",
        "-y",
        "-re",
        "-i",
        "rtmp://ingest.example.com/live/key",
        "-c",
        "copy",
        "-f",
        "flv",
        "rtmp://twitch.example.com/live/tkey",
    ]


def test_build_args_passthrough_multiple_targets() -> None:
    """N targets -- one `-c copy -f flv <url>` block per enabled target, in order."""
    spec = StreamJobSpec(
        source_url="rtmp://ingest.example.com/live/key",
        targets=[
            ForwardTargetSpec(forward_url="rtmp://twitch.example.com/live/t1"),
            ForwardTargetSpec(forward_url="rtmp://youtube.example.com/live/t2"),
        ],
        transcode=False,
        transcode_bitrate_kbps=4000,
        record_path=None,
    )
    args = build_ffmpeg_args(spec)
    assert args == [
        "ffmpeg",
        "-y",
        "-re",
        "-i",
        "rtmp://ingest.example.com/live/key",
        "-c",
        "copy",
        "-f",
        "flv",
        "rtmp://twitch.example.com/live/t1",
        "-c",
        "copy",
        "-f",
        "flv",
        "rtmp://youtube.example.com/live/t2",
    ]


def test_build_args_transcode_applies_codec_flags_per_output() -> None:
    """Transcode admitted -- real libx264/aac codec flags, bitrate from config, per target."""
    spec = StreamJobSpec(
        source_url="https://example.com/source.m3u8",
        targets=[ForwardTargetSpec(forward_url="rtmp://target.example.com/live/k")],
        transcode=True,
        transcode_bitrate_kbps=6000,
        record_path=None,
    )
    args = build_ffmpeg_args(spec)
    assert args == [
        "ffmpeg",
        "-y",
        "-re",
        "-i",
        "https://example.com/source.m3u8",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-b:v",
        "6000k",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-f",
        "flv",
        "rtmp://target.example.com/live/k",
    ]


def test_build_args_with_recording() -> None:
    """Recording appends a `-c copy -f mp4 <path>` output block, independent of transcode."""
    spec = StreamJobSpec(
        source_url="rtmp://ingest.example.com/live/key",
        targets=[ForwardTargetSpec(forward_url="rtmp://target.example.com/live/k")],
        transcode=False,
        transcode_bitrate_kbps=4000,
        record_path="/recordings/community-1.mp4",
    )
    args = build_ffmpeg_args(spec)
    assert args[-5:] == ["-c", "copy", "-f", "mp4", "/recordings/community-1.mp4"]


def test_build_args_recording_only_no_targets() -> None:
    """Zero targets but recording enabled is a valid job (record without forwarding)."""
    spec = StreamJobSpec(
        source_url="rtmp://ingest.example.com/live/key",
        targets=[],
        transcode=False,
        transcode_bitrate_kbps=4000,
        record_path="/recordings/community-1.mp4",
    )
    args = build_ffmpeg_args(spec)
    assert args == [
        "ffmpeg",
        "-y",
        "-re",
        "-i",
        "rtmp://ingest.example.com/live/key",
        "-c",
        "copy",
        "-f",
        "mp4",
        "/recordings/community-1.mp4",
    ]


def test_build_args_rejects_nothing_to_do() -> None:
    """Zero targets and no recording -- refuses to build a no-op ffmpeg invocation."""
    spec = StreamJobSpec(
        source_url="rtmp://ingest.example.com/live/key",
        targets=[],
        transcode=False,
        transcode_bitrate_kbps=4000,
        record_path=None,
    )
    with pytest.raises(ValueError, match="at least one enabled target or recording"):
        build_ffmpeg_args(spec)


def test_build_args_custom_binary_path() -> None:
    """`ffmpeg_binary` override is honored as argv[0]."""
    spec = StreamJobSpec(
        source_url="rtmp://ingest.example.com/live/key",
        targets=[ForwardTargetSpec(forward_url="rtmp://target.example.com/live/k")],
        transcode=False,
        transcode_bitrate_kbps=4000,
        record_path=None,
    )
    args = build_ffmpeg_args(spec, ffmpeg_binary="/usr/bin/ffmpeg")
    assert args[0] == "/usr/bin/ffmpeg"


class TestFFmpegSupervisor:
    """Real subprocess lifecycle logic, against `FakeSubprocessExec` only."""

    @pytest.mark.asyncio
    async def test_start_tracks_pid_and_execs_given_args(self) -> None:
        fake_exec = FakeSubprocessExec()
        supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)
        managed = await supervisor.start(1, ["ffmpeg", "-i", "src", "-f", "flv", "dst"])
        assert managed.pid == fake_exec.processes[0].pid
        assert fake_exec.calls[0] == ("ffmpeg", "-i", "src", "-f", "flv", "dst")
        assert supervisor.is_running(1) is True

    @pytest.mark.asyncio
    async def test_start_raises_if_already_running_for_config(self) -> None:
        fake_exec = FakeSubprocessExec()
        supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)
        await supervisor.start(1, ["ffmpeg", "-i", "src", "-f", "flv", "dst"])
        with pytest.raises(RuntimeError, match="already running"):
            await supervisor.start(1, ["ffmpeg", "-i", "src2", "-f", "flv", "dst2"])

    @pytest.mark.asyncio
    async def test_is_running_false_for_unknown_config(self) -> None:
        supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
        assert supervisor.is_running(999) is False

    @pytest.mark.asyncio
    async def test_stop_sends_sigterm_and_untracks(self) -> None:
        fake_exec = FakeSubprocessExec()
        supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)
        await supervisor.start(1, ["ffmpeg"])
        await supervisor.stop(1)
        assert fake_exec.processes[0].signals_received == [signal.SIGTERM]
        assert supervisor.is_running(1) is False
        assert supervisor.get(1) is None

    @pytest.mark.asyncio
    async def test_stop_is_idempotent_noop_for_unknown_config(self) -> None:
        supervisor = FFmpegSupervisor(subprocess_exec=FakeSubprocessExec())
        await supervisor.stop(12345)  # must not raise

    @pytest.mark.asyncio
    async def test_stop_force_kills_after_grace_period_expires(self) -> None:
        """A process that ignores SIGTERM (never sets returncode) gets SIGKILL."""

        class _StubbornProcess:
            def __init__(self) -> None:
                self.pid = 42
                self.returncode: int | None = None
                self.killed = False

            def send_signal(self, sig: int) -> None:
                pass  # ignores SIGTERM -- never sets returncode

            def kill(self) -> None:
                self.killed = True
                self.returncode = -9

            async def wait(self) -> int:
                if not self.killed:
                    # Never resolves on its own -- forces the supervisor's
                    # timeout path, matching a real hung ffmpeg process.
                    import asyncio

                    await asyncio.Event().wait()
                return self.returncode  # type: ignore[return-value]

        stubborn = _StubbornProcess()

        async def _exec(*_args: object, **_kwargs: object) -> _StubbornProcess:
            return stubborn

        supervisor = FFmpegSupervisor(subprocess_exec=_exec)
        await supervisor.start(1, ["ffmpeg"])
        await supervisor.stop(1, grace_seconds=0.05)
        assert stubborn.killed is True

    @pytest.mark.asyncio
    async def test_stop_all_stops_every_tracked_job(self) -> None:
        fake_exec = FakeSubprocessExec()
        supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)
        await supervisor.start(1, ["ffmpeg"])
        await supervisor.start(2, ["ffmpeg"])
        await supervisor.stop_all()
        assert supervisor.is_running(1) is False
        assert supervisor.is_running(2) is False

    @pytest.mark.asyncio
    async def test_is_running_false_once_process_exits_on_its_own(self) -> None:
        """A process that exits without `stop()` being called (crash) is reported not-running."""
        fake_exec = FakeSubprocessExec()
        supervisor = FFmpegSupervisor(subprocess_exec=fake_exec)
        await supervisor.start(1, ["ffmpeg"])
        fake_exec.processes[0].returncode = 1  # simulate an ffmpeg crash
        assert supervisor.is_running(1) is False


def test_ensure_recordings_dir_creates_missing_dirs(tmp_path: object) -> None:
    from pathlib import Path

    target = Path(str(tmp_path)) / "nested" / "recordings"  # type: ignore[arg-type]
    assert not target.exists()
    ensure_recordings_dir(str(target))
    assert target.is_dir()


def test_recording_path_is_deterministic_and_collision_free() -> None:
    path = recording_path("/recordings", 7, "2026-09-01T10:00:00+00:00")
    assert path == "/recordings/community-7-2026-09-01T10-00-00+00-00.mp4"
