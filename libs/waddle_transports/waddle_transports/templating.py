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


def _lookup_value(template_key: str, payload: Mapping[str, Any]) -> Any:
    """Resolve a dotted `{{a.b}}` key against `payload`; unresolvable paths sentinel to `""`."""
    value: Any = payload
    for part in template_key.split("."):
        if isinstance(value, Mapping) and part in value:
            value = value[part]
        else:
            return ""
    return value


def render_template(template: str, payload: Mapping[str, Any]) -> str:
    """Render `{{key}}`/`{{a.b}}` placeholders against `payload`; unknown keys render empty.

    Plain `str()` substitution -- for non-JSON contexts only (IRC/email
    plain-text bodies). A JSON `body_template` MUST use
    `render_json_template()`/`build_body()` instead, which JSON-escapes
    each substituted value so payload content can never break out of the
    surrounding JSON string it's substituted into.
    """

    def _lookup(match: re.Match[str]) -> str:
        return str(_lookup_value(match.group(1), payload))

    return _TEMPLATE_VAR_RE.sub(_lookup, template)


def render_json_template(template: str, payload: Mapping[str, Any]) -> str:
    r"""Render `{{key}}`/`{{a.b}}` into a JSON body template, JSON-escaping each value.

    Same lookup semantics as `render_template()`, but every substituted
    value is JSON-string-escaped (quotes, backslashes, control chars, ...)
    before insertion -- a payload value like `",\"admin\":true` renders as
    inert string content, never as a sibling JSON field breaking out of
    the template's own `"{{key}}"` string literal.
    """

    def _lookup(match: re.Match[str]) -> str:
        value = _lookup_value(match.group(1), payload)
        # json.dumps(str(value)) always produces a double-quoted JSON
        # string literal -- strip the surrounding quotes, since the
        # template itself already supplies them (`"{{key}}"`).
        return json.dumps(str(value))[1:-1]

    return _TEMPLATE_VAR_RE.sub(_lookup, template)


def build_body(body_template: str | None, payload: Mapping[str, Any]) -> bytes:
    """Render `body_template` (JSON-escaped) against `payload`, or JSON-serialize `payload`."""
    if body_template:
        return render_json_template(body_template, payload).encode("utf-8")
    return json.dumps(dict(payload)).encode("utf-8")
