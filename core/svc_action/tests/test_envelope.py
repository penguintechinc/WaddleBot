"""services/envelope.py -- parse_envelope against the shared `StageEnvelope` wire shape."""

from __future__ import annotations

import json

import pytest
from flask_core import StageEnvelope

from services.envelope import ActionEnvelope, EnvelopeError, parse_envelope


def _raw(**overrides: object) -> str:
    base: dict[str, object] = {
        "tenant": "acme-corp",
        "community": "42",
        "app_id": "waddles.bot.shoutout.default",
        "stage": "action",
        "event": {
            "platform": "twitch",
            "event_type": "chat_message",
            "actor": "some-user",
            "payload": {"message": "hello"},
            "occurred_at": "2026-08-31T12:00:00Z",
        },
        "ts": "2026-08-31T12:00:00Z",
    }
    base.update(overrides)
    return json.dumps(base)


def test_action_envelope_is_the_shared_stage_envelope_not_a_second_type() -> None:
    """No two envelope types -- `ActionEnvelope` is the exact `StageEnvelope` class."""
    assert ActionEnvelope is StageEnvelope


def test_parses_valid_envelope() -> None:
    envelope = parse_envelope(_raw())
    assert envelope.tenant == "acme-corp"
    assert envelope.community == "42"
    assert envelope.app_id == "waddles.bot.shoutout.default"
    assert envelope.event.payload == {"message": "hello"}
    assert envelope.event.platform == "twitch"


def test_parses_bytes_input() -> None:
    envelope = parse_envelope(_raw().encode("utf-8"))
    assert envelope.tenant == "acme-corp"


def test_tenant_wide_community_is_none() -> None:
    envelope = parse_envelope(_raw(community=None))
    assert envelope.community is None


def test_malformed_json_raises() -> None:
    with pytest.raises(EnvelopeError, match="not valid JSON"):
        parse_envelope("{not json")


def test_non_object_json_raises() -> None:
    with pytest.raises(EnvelopeError, match="JSON object"):
        parse_envelope("[1, 2, 3]")


@pytest.mark.parametrize("missing_key", ["tenant", "app_id", "stage", "ts", "event"])
def test_missing_required_field_raises(missing_key: str) -> None:
    data = json.loads(_raw())
    del data[missing_key]
    with pytest.raises(EnvelopeError):
        parse_envelope(json.dumps(data))


def test_wrong_stage_raises() -> None:
    with pytest.raises(EnvelopeError, match="not 'action'"):
        parse_envelope(_raw(stage="process"))


def test_community_wrong_type_raises() -> None:
    with pytest.raises(EnvelopeError, match="community"):
        parse_envelope(_raw(community=42))


def test_event_payload_wrong_type_raises() -> None:
    data = json.loads(_raw())
    data["event"]["payload"] = "not-a-dict"
    with pytest.raises(EnvelopeError, match="payload"):
        parse_envelope(json.dumps(data))


def test_legacy_top_level_payload_shape_is_refused_not_coerced() -> None:
    """Pre-Wave-2 wire shape (`payload` at the top level, no `event` key) is a hard reject."""
    legacy = {
        "tenant": "acme-corp",
        "community": "42",
        "app_id": "waddles.bot.shoutout.default",
        "stage": "action",
        "payload": {"message": "hello"},
        "ts": "2026-08-31T12:00:00Z",
    }
    with pytest.raises(EnvelopeError):
        parse_envelope(json.dumps(legacy))
