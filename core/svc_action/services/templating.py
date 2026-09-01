"""Shared `{{key}}`/`{{a.b}}` template rendering for adapter body/subject templates.

One rendering pass used by `webhook`, `rest_api`, and `email` adapters --
kept here instead of duplicated per-adapter (or imported from another
adapter's private helper) so it has one docstring, one test file, and one
place to fix if the substitution grammar ever changes.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from services.action_target import ActionTarget
from services.envelope import ActionEnvelope

_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def render_template(template: str, payload: Mapping[str, Any]) -> str:
    """Render `{{key}}`/`{{a.b}}` placeholders against `payload`; unknown keys render empty."""

    def _lookup(match: "re.Match[str]") -> str:
        value: Any = payload
        for part in match.group(1).split("."):
            if isinstance(value, Mapping) and part in value:
                value = value[part]
            else:
                return ""
        return str(value)

    return _TEMPLATE_VAR_RE.sub(_lookup, template)


def build_body(target: ActionTarget, envelope: ActionEnvelope) -> bytes:
    """Render `target.body_template` against the envelope payload, or JSON-serialize it as-is."""
    if target.body_template:
        rendered = render_template(target.body_template, envelope.payload)
        return rendered.encode("utf-8")
    return json.dumps(dict(envelope.payload)).encode("utf-8")
