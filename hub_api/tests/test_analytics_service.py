"""`services/analytics_service.py` -- unit tests for the pure envelope-unwrapping helpers.

`tests/test_v1_analytics_blueprint.py` exercises `_unwrap`/`_relay`
indirectly through every route's happy/failure path; this file closes the
gap on `_unwrap`'s defensive fallback branches (a non-enveloped dict body,
and a non-dict/`None` body) that no route naturally produces since
`analytics-core` always returns a proper envelope in practice.
"""

from __future__ import annotations

from services.analytics_service import _unwrap


class TestUnwrap:
    def test_enveloped_dict_unwraps_data_key(self) -> None:
        assert _unwrap({"success": True, "data": {"total_users": 5}}) == {"total_users": 5}

    def test_non_enveloped_dict_passes_through(self) -> None:
        """No `data` key -- Node's `data.data || data` falls back to the body itself."""
        assert _unwrap({"total_users": 5}) == {"total_users": 5}

    def test_none_body_is_empty_dict(self) -> None:
        assert _unwrap(None) == {}

    def test_non_dict_body_is_empty_dict(self) -> None:
        assert _unwrap("not a dict") == {}
