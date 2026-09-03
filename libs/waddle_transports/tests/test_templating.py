"""templating.py -- `{{key}}` substitution, plain and JSON-escaped."""

from __future__ import annotations

import json

from waddle_transports.templating import build_body, render_json_template, render_template


class TestRenderTemplate:
    """Plain (non-JSON-escaping) substitution -- used for IRC/email plain-text bodies."""

    def test_substitutes_top_level_key(self) -> None:
        assert render_template("hi {{name}}", {"name": "bob"}) == "hi bob"

    def test_substitutes_nested_key(self) -> None:
        assert render_template("{{user.name}}", {"user": {"name": "bob"}}) == "bob"

    def test_unknown_key_renders_empty(self) -> None:
        assert render_template("{{missing}}", {}) == ""

    def test_does_not_escape_special_characters(self) -> None:
        """Plain `render_template` is for non-JSON contexts -- no escaping applied."""
        assert render_template('{{v}}', {"v": 'a"b\\c'}) == 'a"b\\c'


class TestRenderJsonTemplate:
    """JSON-escaping substitution -- used by `build_body()` for JSON body templates."""

    def test_substitutes_plain_value_unchanged(self) -> None:
        assert render_json_template('{"user": "{{name}}"}', {"name": "bob"}) == (
            '{"user": "bob"}'
        )

    def test_escapes_double_quote_so_it_cannot_break_out_of_the_json_string(self) -> None:
        rendered = render_json_template('{"user": "{{name}}"}', {"name": 'bob"'})
        parsed = json.loads(rendered)
        assert parsed == {"user": 'bob"'}

    def test_payload_cannot_inject_a_sibling_json_field(self) -> None:
        r"""Fail-first regression for JSON body-template injection.

        A payload value carrying `",\"admin\":true` must not inject a
        sibling JSON field into the rendered body -- it must render as
        inert *string content*, not break out of the JSON string it was
        substituted into.
        """
        rendered = render_json_template(
            '{"user": "{{name}}"}', {"name": '",\"admin\":true'}
        )
        parsed = json.loads(rendered)
        assert parsed == {"user": '",\"admin\":true'}
        assert "admin" not in parsed
        assert set(parsed.keys()) == {"user"}

    def test_escapes_backslash(self) -> None:
        rendered = render_json_template('{"path": "{{p}}"}', {"p": "C:\\temp"})
        assert json.loads(rendered) == {"path": "C:\\temp"}

    def test_escapes_embedded_newline(self) -> None:
        rendered = render_json_template('{"msg": "{{m}}"}', {"m": "line1\nline2"})
        assert json.loads(rendered) == {"msg": "line1\nline2"}

    def test_unknown_key_renders_empty(self) -> None:
        assert render_json_template('{"v": "{{missing}}"}', {}) == '{"v": ""}'


class TestBuildBody:
    def test_no_template_serializes_payload_as_json(self) -> None:
        body = build_body(None, {"a": 1})
        assert json.loads(body) == {"a": 1}

    def test_template_uses_json_escaping_not_plain_substitution(self) -> None:
        """Fail-first regression for JSON body-template injection.

        `build_body()` must render JSON-safely, not via plain
        `render_template()` str() substitution (which lets payload content
        break out of the surrounding JSON string).
        """
        body = build_body('{"user": "{{name}}"}', {"name": '",\"admin\":true'})
        parsed = json.loads(body)
        assert parsed == {"user": '",\"admin\":true'}
        assert "admin" not in parsed
