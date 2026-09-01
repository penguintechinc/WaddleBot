"""
GDPR retention-bound tests for StreamPipeline.

`waddles:t:{tenant}:{stage}` and its DLQ are append-only Redis Streams --
an unbounded stream is an unbounded retention period. The main stream
write already took `maxlen`; the DLQ write did not (poison events, which
sit longest, were exempt from the one control that matters most for
them). This suite asserts every stream write StreamPipeline performs is
bounded, and that the bound actually trims.
"""

from __future__ import annotations

import pytest


pytestmark = pytest.mark.asyncio


async def test_dlq_maxlen_has_a_sane_default(pipeline):
    """DLQ retention is a config knob with a default, not left unset."""
    assert pipeline.dlq_maxlen == pipeline.DEFAULT_DLQ_MAXLEN
    assert pipeline.dlq_maxlen > 0


async def test_dlq_maxlen_is_configurable(fake_redis, stream_pipeline_module):
    """Callers can override the DLQ bound (constructor arg wins over env default)."""
    p = stream_pipeline_module.StreamPipeline(
        redis_url="redis://fake", enabled=True, dlq_maxlen=5
    )
    p._redis = fake_redis
    p._connected = True
    assert p.dlq_maxlen == 5


async def test_dlq_past_its_bound_is_trimmed(pipeline, fake_redis):
    """Pushing well past dlq_maxlen entries leaves the DLQ at or below the bound.

    This is the test that must fail against the unbounded `xadd(dlq_name,
    dlq_data)` call and pass once `move_to_dlq` supplies `maxlen`.
    """
    pipeline.dlq_maxlen = 10
    total_events = 50

    for i in range(total_events):
        ok = await pipeline.move_to_dlq(
            stream_name="events:commands",
            message_id=f"{i}-0",
            error_reason="max_retries_exceeded",
            event_data={"user_id": "11111111-1111-1111-1111-111111111111"},
            retry_count=3,
        )
        assert ok is True

    dlq_name = pipeline._make_dlq_name(pipeline._make_stream_name("events:commands"))
    final_len = await fake_redis.xlen(dlq_name)

    assert final_len <= pipeline.dlq_maxlen, (
        f"DLQ grew to {final_len} entries, exceeding its {pipeline.dlq_maxlen} bound "
        "-- unbounded retention (GDPR)"
    )
    assert final_len == pipeline.dlq_maxlen


async def test_main_stream_past_its_bound_is_trimmed(pipeline, fake_redis):
    """The main stream write's existing maxlen support actually trims."""
    max_len = 10
    total_events = 30

    for i in range(total_events):
        message_id = await pipeline.publish_event(
            stream_name="events:commands",
            event_data={"command_id": str(i)},
            max_len=max_len,
        )
        assert message_id is not None

    full_stream_name = pipeline._make_stream_name("events:commands")
    final_len = await fake_redis.xlen(full_stream_name)

    assert final_len <= max_len
    assert final_len == max_len


async def test_every_xadd_call_site_supplies_a_bound(pipeline, fake_redis):
    """Regression guard: both stream-write paths must pass `maxlen`, unconditionally.

    Wraps the fake's xadd to record whether maxlen was supplied on every
    call, so a future call site added without a bound fails this test
    rather than silently shipping unbounded retention.
    """
    calls: list[tuple[str, object]] = []
    original_xadd = fake_redis.xadd

    async def recording_xadd(name, fields, maxlen=None, approximate=True, id="*"):
        calls.append((name, maxlen))
        return await original_xadd(name, fields, maxlen=maxlen, approximate=approximate, id=id)

    fake_redis.xadd = recording_xadd  # type: ignore[method-assign]

    await pipeline.publish_event("events:commands", {"command": "translate"}, max_len=100)
    await pipeline.move_to_dlq(
        "events:commands", "1-0", "bad_payload", event_data={"x": "y"}
    )

    assert len(calls) == 2
    for stream_name, maxlen in calls:
        assert maxlen is not None, f"xadd to {stream_name} has no maxlen -- unbounded retention"
