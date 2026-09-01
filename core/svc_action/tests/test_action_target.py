"""services/action_target.py -- parse_action_target validation for all 5 types."""

from __future__ import annotations

import pytest

from services.action_target import ActionTargetError, parse_action_target


def test_webhook_requires_url_and_secret_ref() -> None:
    target = parse_action_target(
        {"type": "webhook", "url": "https://example.com/hook", "secret_ref": "WEBHOOK_SECRET"}
    )
    assert target.type == "webhook"
    assert target.url == "https://example.com/hook"
    assert target.secret_ref == "WEBHOOK_SECRET"


def test_webhook_missing_url_raises() -> None:
    with pytest.raises(ActionTargetError, match="url"):
        parse_action_target({"type": "webhook", "secret_ref": "WEBHOOK_SECRET"})


def test_webhook_missing_secret_ref_raises() -> None:
    with pytest.raises(ActionTargetError, match="secret_ref"):
        parse_action_target({"type": "webhook", "url": "https://example.com/hook"})


def test_rest_api_defaults_method_to_post() -> None:
    target = parse_action_target({"type": "rest_api", "url": "https://example.com/api"})
    assert target.method == "POST"


def test_rest_api_rejects_unknown_method() -> None:
    with pytest.raises(ActionTargetError, match="method"):
        parse_action_target(
            {"type": "rest_api", "url": "https://example.com/api", "method": "TRACE"}
        )


def test_rest_api_uppercases_method() -> None:
    target = parse_action_target(
        {"type": "rest_api", "url": "https://example.com/api", "method": "get"}
    )
    assert target.method == "GET"


def test_message_queue_requires_channel() -> None:
    target = parse_action_target({"type": "message_queue", "channel": "waddles:notify"})
    assert target.channel == "waddles:notify"


def test_message_queue_missing_channel_raises() -> None:
    with pytest.raises(ActionTargetError, match="channel"):
        parse_action_target({"type": "message_queue"})


def test_overlay_requires_surface() -> None:
    target = parse_action_target({"type": "overlay", "surface": "giveaway"})
    assert target.surface == "giveaway"
    assert target.community is None


def test_overlay_missing_surface_raises() -> None:
    with pytest.raises(ActionTargetError, match="surface"):
        parse_action_target({"type": "overlay"})


def test_overlay_community_must_be_string() -> None:
    with pytest.raises(ActionTargetError, match="community"):
        parse_action_target({"type": "overlay", "surface": "giveaway", "community": 123})


def test_email_requires_to_and_subject_template() -> None:
    target = parse_action_target(
        {
            "type": "email",
            "to": ["ops@example.com"],
            "subject_template": "Alert: {{event}}",
        }
    )
    assert target.to_addrs == ("ops@example.com",)
    assert target.subject_template == "Alert: {{event}}"


def test_email_missing_to_raises() -> None:
    with pytest.raises(ActionTargetError, match="to"):
        parse_action_target({"type": "email", "subject_template": "Alert"})


def test_email_empty_to_list_raises() -> None:
    with pytest.raises(ActionTargetError, match="to"):
        parse_action_target({"type": "email", "to": [], "subject_template": "Alert"})


def test_email_missing_subject_template_raises() -> None:
    with pytest.raises(ActionTargetError, match="subject_template"):
        parse_action_target({"type": "email", "to": ["ops@example.com"]})


def test_unknown_type_raises() -> None:
    with pytest.raises(ActionTargetError, match="not one of"):
        parse_action_target({"type": "carrier_pigeon"})


def test_missing_type_raises() -> None:
    with pytest.raises(ActionTargetError):
        parse_action_target({})
