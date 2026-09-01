"""services/envelope.py -- parse_envelope validation."""

from __future__ import annotations

import json

import pytest

from services.envelope import EnvelopeError, parse_envelope


def _raw(**overrides: object) -> str:
    base = {
        "tenant": "1",
        "community": "42",
        "app_id": "waddles.bot.shoutout.default",
        "stage": "action",
        "payload": {"message": "hello"},
        "ts": "2026-08-31T12:00:00Z",
    }
    base.update(overrides)
    return json.dumps(base)


def test_parses_valid_envelope() -> None:
    envelope = parse_envelope(_raw())
    assert envelope.tenant == "1"
    assert envelope.community == "42"
    assert envelope.app_id == "waddles.bot.shoutout.default"
    assert envelope.payload == {"message": "hello"}


def test_parses_bytes_input() -> None:
    envelope = parse_envelope(_raw().encode("utf-8"))
    assert envelope.tenant == "1"


def test_tenant_wide_community_is_none() -> None:
    envelope = parse_envelope(_raw(community=None))
    assert envelope.community is None


def test_malformed_json_raises() -> None:
    with pytest.raises(EnvelopeError, match="not valid JSON"):
        parse_envelope("{not json")


def test_non_object_json_raises() -> None:
    with pytest.raises(EnvelopeError, match="JSON object"):
        parse_envelope("[1, 2, 3]")


@pytest.mark.parametrize("missing_key", ["tenant", "app_id", "stage", "ts"])
def test_missing_required_field_raises(missing_key: str) -> None:
    data = json.loads(_raw())
    del data[missing_key]
    with pytest.raises(EnvelopeError, match=missing_key):
        parse_envelope(json.dumps(data))


def test_wrong_stage_raises() -> None:
    with pytest.raises(EnvelopeError, match="not 'action'"):
        parse_envelope(_raw(stage="process"))


def test_community_wrong_type_raises() -> None:
    with pytest.raises(EnvelopeError, match="community"):
        parse_envelope(_raw(community=42))


def test_payload_wrong_type_raises() -> None:
    with pytest.raises(EnvelopeError, match="payload"):
        parse_envelope(_raw(payload="not-a-dict"))
