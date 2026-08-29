"""Generic-contract tests for StreamPipeline (Task 0.3b: split the router).

StreamPipeline is the Core event bus library — every stage links against it
to publish/consume opaque events on Valkey/Redis Streams. It must carry zero
platform or command vocabulary; callers (e.g. Bot's command_processor) own
the meaning of an event's `type` field, the pipeline only moves bytes.
"""

import re
from pathlib import Path

STREAM_PIPELINE_SRC = (
    Path(__file__).resolve().parent.parent / "flask_core" / "stream_pipeline.py"
)


def test_stream_pipeline_carries_no_domain_vocabulary() -> None:
    """Regression guard for the router split: no Twitch/Discord/command/emote leakage.

    Mirrors the plan's verify gate:
    grep -riE "twitch|discord|emote|command" libs/flask_core/flask_core/stream_pipeline.py
    """
    text = STREAM_PIPELINE_SRC.read_text()
    leaks = re.findall(r"twitch|discord|emote|command", text, re.IGNORECASE)
    assert leaks == [], f"domain vocabulary leaked into the generic event bus: {leaks}"


async def test_publish_consume_ack_roundtrip(pipeline) -> None:
    """An opaque event type moves through publish -> consume -> ack cleanly."""
    message_id = await pipeline.publish_event(
        "events:process", {"type": "widget.created", "widget_id": "w-1"}
    )
    assert message_id is not None

    events = await pipeline.consume_events(
        "events:process", consumer_group="test-group", consumer_name="consumer-1"
    )
    assert len(events) == 1
    assert events[0]["data"] == {"type": "widget.created", "widget_id": "w-1"}
    assert events[0]["retry_count"] == 0

    acked = await pipeline.acknowledge_event(
        "events:process", consumer_group="test-group", message_id=events[0]["id"]
    )
    assert acked is True

    # Acked message is no longer pending redelivery.
    pending = await pipeline.get_pending_events(
        "events:process", consumer_group="test-group"
    )
    assert pending == []


async def test_unacked_event_remains_pending_until_acked(pipeline) -> None:
    """A consumed-but-not-acked event stays in the pending entries list (at-least-once)."""
    await pipeline.publish_event("events:process", {"type": "widget.created"})
    events = await pipeline.consume_events(
        "events:process", consumer_group="test-group", consumer_name="consumer-1"
    )
    assert len(events) == 1

    pending = await pipeline.get_pending_events(
        "events:process", consumer_group="test-group"
    )
    assert len(pending) == 1
    assert pending[0]["message_id"] == events[0]["id"]


async def test_poison_event_moves_to_dlq(pipeline) -> None:
    """A poison event lands in the DLQ with its failure reason and original payload."""
    await pipeline.publish_event("events:process", {"type": "widget.created"})
    events = await pipeline.consume_events(
        "events:process", consumer_group="test-group", consumer_name="consumer-1"
    )
    assert len(events) == 1
    event = events[0]

    moved = await pipeline.move_to_dlq(
        "events:process",
        message_id=event["id"],
        error_reason="max_retries_exceeded",
        event_data=event["data"],
        retry_count=3,
    )
    assert moved is True

    await pipeline.acknowledge_event(
        "events:process", consumer_group="test-group", message_id=event["id"]
    )

    dlq_events = await pipeline.get_dlq_events("events:process")
    assert len(dlq_events) == 1
    assert dlq_events[0]["failure_reason"] == "max_retries_exceeded"
    assert dlq_events[0]["original_id"] == event["id"]
    assert dlq_events[0]["data"] == {"type": "widget.created"}

    # Original stream's pending list is clear — the poison event isn't retried forever.
    pending = await pipeline.get_pending_events(
        "events:process", consumer_group="test-group"
    )
    assert pending == []


async def test_consumer_group_creation_is_idempotent(pipeline) -> None:
    """Re-consuming re-creates the group without raising (BUSYGROUP handled internally)."""
    await pipeline.publish_event("events:process", {"type": "widget.created"})
    first = await pipeline.consume_events(
        "events:process", consumer_group="test-group", consumer_name="consumer-1"
    )
    assert len(first) == 1

    # Second call creates the same group again — must not raise, must not redeliver
    # anything new since nothing else was published.
    second = await pipeline.consume_events(
        "events:process", consumer_group="test-group", consumer_name="consumer-2"
    )
    assert second == []
