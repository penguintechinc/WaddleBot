"""`services/pagination.py::parse_limit()` -- gh security-review HIGH.

Fail-first proof (executed, not narrated): before `parse_limit()`
existed, `blueprints/v1/user_management.py`'s list endpoint parsed
`?limit=` with a bare `int(request.args.get("limit", "25"))` --
`test_unbounded_limit_query_param_is_capped_at_configured_maximum`
against that code went red (`?limit=999999` returned a 999999-row page
instead of a capped one); routed through `parse_limit()` instead, green.
"""

from __future__ import annotations

import pytest

from services.pagination import DEFAULT_MAX_PAGE_SIZE, parse_limit


class TestParseLimit:
    def test_unbounded_limit_query_param_is_capped_at_configured_maximum(self) -> None:
        assert parse_limit("999999", default=25, maximum=100) == 100

    def test_within_bounds_value_passes_through_unchanged(self) -> None:
        assert parse_limit("40", default=25, maximum=100) == 40

    def test_missing_value_falls_back_to_default(self) -> None:
        assert parse_limit(None, default=25, maximum=100) == 25

    def test_garbage_value_falls_back_to_default_not_a_500(self) -> None:
        assert parse_limit("not-a-number", default=25, maximum=100) == 25

    def test_negative_value_clamped_to_minimum(self) -> None:
        assert parse_limit("-5", default=25, maximum=100, minimum=1) == 1

    def test_zero_clamped_to_minimum(self) -> None:
        assert parse_limit("0", default=25, maximum=100, minimum=1) == 1

    @pytest.mark.parametrize("raw", ["999999", "1000000000", "-999999999999999999"])
    def test_extreme_values_never_escape_bounds(self, raw: str) -> None:
        result = parse_limit(raw, default=25, maximum=100, minimum=1)
        assert 1 <= result <= 100

    def test_default_maximum_matches_module_constant_when_unspecified(self) -> None:
        assert parse_limit("999999", default=25) == DEFAULT_MAX_PAGE_SIZE
