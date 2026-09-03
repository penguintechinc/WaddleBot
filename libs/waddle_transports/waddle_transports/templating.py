"""Shared `{{key}}`/`{{a.b}}` template rendering for transport body/subject templates.

One rendering pass used by `http` (webhook/rest_api body), `email`
(subject/body) -- kept here instead of duplicated per-transport so it has
one docstring, one test file, one place to fix if the substitution
grammar ever changes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from typing import Any

_TEMPLATE_VAR_RE = re.compile(r"\{\{\s*([\w.]+)\s*\}\}")


def render_template(template: str, payload: Mapping[str, Any]) -> str:
    """Render `{{key}}`/`{{a.b}}` placeholders against `payload`; unknown keys render empty."""

    def _lookup(match: re.Match[str]) -> str:
        value: Any = payload
        for part in match.group(1).split("."):
            if isinstance(value, Mapping) and part in value:
                value = value[part]
            else:
                return ""
        return str(value)

    return _TEMPLATE_VAR_RE.sub(_lookup, template)


def build_body(body_template: str | None, payload: Mapping[str, Any]) -> bytes:
    """Render `body_template` against `payload`, or JSON-serialize `payload` as-is if unset."""
    if body_template:
        return render_template(body_template, payload).encode("utf-8")
    return json.dumps(dict(payload)).encode("utf-8")
