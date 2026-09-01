"""services/templating.py -- `{{key}}`/`{{a.b}}` rendering + body building."""

from __future__ import annotations

import json

from services.action_target import ActionTarget
from services.envelope import ActionEnvelope
from services.templating import build_body, render_template


def _envelope(payload: dict) -> ActionEnvelope:
    return ActionEnvelope(
        tenant="1",
        community="42",
        app_id="waddles.bot.shoutout.default",
        stage="action",
        payload=payload,
        ts="2026-08-31T12:00:00Z",
        raw="{}",
    )


def test_render_template_substitutes_top_level_key() -> None:
    assert render_template("Hello {{name}}!", {"name": "World"}) == "Hello World!"


def test_render_template_substitutes_nested_key() -> None:
    assert render_template("{{user.name}}", {"user": {"name": "Justin"}}) == "Justin"


def test_render_template_unknown_key_renders_empty() -> None:
    assert render_template("[{{missing}}]", {}) == "[]"


def test_render_template_no_placeholders_passthrough() -> None:
    assert render_template("no placeholders here", {"x": 1}) == "no placeholders here"


def test_build_body_uses_template_when_present() -> None:
    target = ActionTarget(
        type="webhook",
        url="https://example.com",
        secret_ref="S",
        body_template='{"user":"{{name}}"}',
    )
    envelope = _envelope({"name": "Justin"})
    assert build_body(target, envelope) == b'{"user":"Justin"}'


def test_build_body_falls_back_to_json_payload() -> None:
    target = ActionTarget(type="webhook", url="https://example.com", secret_ref="S")
    envelope = _envelope({"name": "Justin"})
    assert json.loads(build_body(target, envelope)) == {"name": "Justin"}
