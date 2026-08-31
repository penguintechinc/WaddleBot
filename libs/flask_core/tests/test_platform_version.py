"""Canonical PLATFORM_VERSION + App Bundle platform-compatibility (FORK6).

Covers `get_platform_version` (reads/validates `flask_core/VERSION`) and
`platform_version_compatible` (block/warn/ok policy against a bundle's
declared `platform_compatibility`). Imported as leaf submodules -- like
`test_bundle_isolation_keys.py` -- since `platform_version.py` only depends
on `app_manifest.py` (stdlib-only), bypassing the heavy `flask_core/__init__`
import chain (pydal/quart/authlib) via the `conftest.py` package stub.
"""

from __future__ import annotations

import pytest

from flask_core.app_manifest import PlatformCompat
from flask_core.platform_version import get_platform_version, platform_version_compatible


def test_get_platform_version_returns_v3_semver() -> None:
    """The canonical source reflects the repo's actual release/v3.0.X line.

    flask_core/VERSION is package data (see MANIFEST.in) so this same read
    resolves identically from the monorepo checkout and from every service
    container that only ever gets `COPY libs/flask_core` + `pip install .`.
    """
    version = get_platform_version()
    assert version == "3.0.0"


def test_get_platform_version_is_cached_and_stable() -> None:
    """Repeated calls return the identical string (process-lifetime cache)."""
    assert get_platform_version() is get_platform_version()


class TestPlatformVersionCompatible:
    """FORK6 policy: block outside [min,max]; warn in-range-untested; ok on tested match."""

    def test_below_min_version_blocks(self) -> None:
        compat = PlatformCompat(tested_with="", min_version="3.1.0", max_version=None)
        ok, reason = platform_version_compatible(compat)
        assert ok is False
        assert "below" in reason
        assert "3.1.0" in reason

    def test_above_max_version_blocks(self) -> None:
        compat = PlatformCompat(tested_with="", min_version=None, max_version="2.9.0")
        ok, reason = platform_version_compatible(compat)
        assert ok is False
        assert "above" in reason
        assert "2.9.0" in reason

    def test_in_range_but_tested_with_different_version_warns(self) -> None:
        """Bundle was tested against a different (still in-range) platform
        version -- allowed to install/activate, but flagged as untested
        against exactly what's running now.
        """
        compat = PlatformCompat(
            tested_with="2.9.5", min_version="2.0.0", max_version="3.5.0"
        )
        ok, reason = platform_version_compatible(compat)
        assert ok is True
        assert reason != ""
        assert "untested" in reason
        assert "2.9.5" in reason

    def test_tested_with_exact_match_is_ok_with_no_reason(self) -> None:
        compat = PlatformCompat(tested_with="3.0.0", min_version=None, max_version=None)
        ok, reason = platform_version_compatible(compat)
        assert ok is True
        assert reason == ""

    def test_unset_tested_with_in_range_is_ok_no_warning(self) -> None:
        """Empty `tested_with` (legacy manifest, pre-3.4 field) asserts
        nothing -- there is no claim to contradict, so this is OK rather
        than a spurious warning on every pre-existing bundle.
        """
        compat = PlatformCompat(tested_with="", min_version="1.0.0", max_version="4.0.0")
        ok, reason = platform_version_compatible(compat)
        assert ok is True
        assert reason == ""

    def test_no_bounds_declared_defaults_to_in_range(self) -> None:
        compat = PlatformCompat()
        ok, reason = platform_version_compatible(compat)
        assert ok is True
        assert reason == ""

    @pytest.mark.parametrize("min_version", ["3.0.0", "2.5.0"])
    def test_running_version_equal_to_min_is_inclusive_not_blocked(
        self, min_version: str
    ) -> None:
        compat = PlatformCompat(tested_with="", min_version=min_version, max_version=None)
        ok, _reason = platform_version_compatible(compat)
        assert ok is True

    @pytest.mark.parametrize("max_version", ["3.0.0", "3.5.0"])
    def test_running_version_equal_to_max_is_inclusive_not_blocked(
        self, max_version: str
    ) -> None:
        compat = PlatformCompat(tested_with="", min_version=None, max_version=max_version)
        ok, _reason = platform_version_compatible(compat)
        assert ok is True
