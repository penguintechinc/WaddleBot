"""
PII-tokenization guard for the stream envelope (`critical-rules.md` PII
Tokenization).

`waddles:t:{tenant}:{stage}` streams are append-only; GDPR erasure is only
tractable if the envelope carries UUIDs/opaque references, never PII,
since deleting a stream entry selectively is not a thing. This asserts
the envelope's *field set* -- the wrapper StreamPipeline itself writes to
Redis -- against an ALLOWLIST of permitted fields.

Deliberately an allowlist, not a denylist of PII-looking names: a
denylist passes for every field nobody thought of. Anything outside the
allowlist fails the test, whether or not it looks like PII today.

Scope: this covers the transport envelope StreamPipeline constructs
(StreamEvent, and the dicts passed to XADD for the main stream and the
DLQ). The opaque `data`/`event_data` payload it carries is a per-Feature
business-layer concern (tokenization of `EventPayload`/`CommandRequest`
in `datamodels.py`) tracked separately -- see report.
"""

from __future__ import annotations

import dataclasses

import pytest

# Permitted top-level fields for the StreamEvent envelope dataclass.
# Every field here is transport metadata (an ID, a stream name, a retry
# counter, a timestamp) or an opaque payload container -- never a
# PII-shaped field (no email, name, username, ip_address, phone, address).
STREAM_EVENT_ALLOWLIST = frozenset({"id", "stream", "data", "retry_count", "timestamp"})

# Permitted keys in the dict handed to XADD for a main-stream publish.
PUBLISH_ENVELOPE_ALLOWLIST = frozenset({"data", "timestamp", "retry_count"})

# Permitted keys in the dict handed to XADD for a DLQ entry.
DLQ_ENVELOPE_ALLOWLIST = frozenset(
    {"original_id", "original_stream", "failure_reason", "retry_count", "timestamp", "data"}
)


def test_stream_event_dataclass_fields_match_allowlist(stream_pipeline_module):
    """StreamEvent must declare exactly the allowlisted fields -- no more."""
    actual_fields = {f.name for f in dataclasses.fields(stream_pipeline_module.StreamEvent)}
    extra = actual_fields - STREAM_EVENT_ALLOWLIST
    assert not extra, (
        f"StreamEvent has field(s) outside the PII-safe allowlist: {sorted(extra)} -- "
        "flag for review: is this PII-shaped, and if so tokenize to a UUID reference"
    )


@pytest.mark.asyncio
async def test_publish_envelope_fields_match_allowlist(pipeline, fake_redis):
    """The wire dict written for a main-stream publish carries no unexpected field."""
    await pipeline.publish_event(
        "events:commands",
        {"command": "translate", "user_id": "11111111-1111-1111-1111-111111111111"},
        max_len=100,
    )

    full_stream_name = pipeline._make_stream_name("events:commands")
    entries = await fake_redis.xrange(full_stream_name)
    assert len(entries) == 1
    _, written_fields = entries[0]

    extra = set(written_fields.keys()) - PUBLISH_ENVELOPE_ALLOWLIST
    assert not extra, (
        f"publish_event wrote unexpected envelope field(s): {sorted(extra)} -- "
        "not on the PII-safe allowlist"
    )


@pytest.mark.asyncio
async def test_dlq_envelope_fields_match_allowlist(pipeline, fake_redis):
    """The wire dict written for a DLQ entry carries no unexpected field."""
    await pipeline.move_to_dlq(
        "events:commands",
        "1-0",
        "max_retries_exceeded",
        event_data={"user_id": "11111111-1111-1111-1111-111111111111"},
        retry_count=3,
    )

    dlq_name = pipeline._make_dlq_name(pipeline._make_stream_name("events:commands"))
    entries = await fake_redis.xrange(dlq_name)
    assert len(entries) == 1
    _, written_fields = entries[0]

    extra = set(written_fields.keys()) - DLQ_ENVELOPE_ALLOWLIST
    assert not extra, (
        f"move_to_dlq wrote unexpected envelope field(s): {sorted(extra)} -- "
        "not on the PII-safe allowlist"
    )
