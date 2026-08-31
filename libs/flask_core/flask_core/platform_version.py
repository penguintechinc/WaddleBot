"""
Canonical running-platform version + App Bundle platform-compatibility check.

The repo has no single existing artifact that is both (a) authoritative for
"what platform SemVer is actually running" and (b) guaranteed to be present
inside every deployed container. ``.version`` at the repo root drives CI
image tagging (build-epoch suffixed, e.g. ``3.0.0.1787775284``, not strict
SemVer) but every service Dockerfile does ``COPY libs/flask_core ...`` only
-- the repo root never ships into a container, so a repo-root file would
silently 404 at runtime everywhere this library is actually installed.
Similarly ``k8s/helm/waddlebot/Chart.yaml``'s ``appVersion`` and git tags are
monorepo-level artifacts, not something an installed ``flask_core`` package
can read post-install.

So the canonical source lives *inside* the package itself: ``VERSION``,
sibling to this module, shipped as installed package data (see
``libs/flask_core/MANIFEST.in`` + ``setup.py``'s ``include_package_data``).
That guarantees ``Path(__file__).parent / "VERSION"`` resolves identically
whether importing from the monorepo checkout, a test run, or the installed
copy under site-packages in any of the ~40 service containers.

Reuses :data:`flask_core.app_manifest._SEMVER_RE` for all parsing --
no second version grammar.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Tuple

from .app_manifest import PlatformCompat, _SEMVER_RE

_VERSION_FILE = Path(__file__).resolve().parent / "VERSION"


@lru_cache(maxsize=1)
def get_platform_version() -> str:
    """Return the running platform's SemVer string (e.g. ``"3.0.0"``).

    Reads and validates ``flask_core/VERSION`` once per process (cached --
    the platform version cannot change mid-process). Raises ``RuntimeError``
    if the file is missing or its content isn't valid SemVer 2.0.0, so a
    packaging regression fails loudly at first use rather than silently
    comparing against an empty/garbage string.
    """
    try:
        raw = _VERSION_FILE.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(
            f"platform VERSION file not found at {_VERSION_FILE} -- "
            "flask_core packaging is broken (see MANIFEST.in)"
        ) from exc

    if not _SEMVER_RE.match(raw):
        raise RuntimeError(f"platform VERSION file content {raw!r} is not valid SemVer 2.0.0")
    return raw


def _semver_core(version: str) -> Tuple[int, int, int]:
    """Extract the ``(major, minor, patch)`` ordering key from a SemVer string.

    Reuses :data:`_SEMVER_RE` (same grammar app_manifest.py validates
    ``platform_compatibility.min_version``/``max_version`` against) rather
    than a second hand-rolled parser. Pre-release/build metadata is ignored
    for ordering purposes -- min/max bounds here are whole-release gates,
    not pre-release-aware comparisons.
    """
    match = _SEMVER_RE.match(version)
    if not match:
        raise ValueError(f"{version!r} is not valid SemVer 2.0.0")
    major, minor, patch = match.group(1), match.group(2), match.group(3)
    return (int(major), int(minor), int(patch))


def platform_version_compatible(platform_compatibility: PlatformCompat) -> Tuple[bool, str]:
    """Check the running platform version against a bundle's declared compatibility.

    FORK6 enforcement policy (App Bundle SDK spec §3.4/§9 leaves this open;
    resolved here since install/available/activate need one answer):

    - **BLOCK** (``False``, reason) -- running version falls outside
      ``[min_version, max_version]`` (either bound, when declared).
    - **WARN** (``True``, reason) -- in-range (or no bounds declared) but
      ``tested_with`` is a non-empty string that doesn't exactly match the
      running version. ``tested_with`` is documented in
      :class:`PlatformCompat` as free text, not SemVer-validated (it may be
      a release-branch string like ``"release/v3.0.X"``), so exact string
      equality is the only safe comparison -- anything else would require
      guessing at an unspecified grammar.
    - **OK** (``True``, ``""``) -- in-range and either ``tested_with`` is
      unset (no assertion made, nothing to contradict) or matches exactly.

    Pure function, no DB/IO beyond the cached :func:`get_platform_version`
    read -- safe to call from install/available/activate hot paths.
    """
    running = get_platform_version()
    running_key = _semver_core(running)

    if platform_compatibility.min_version is not None:
        if running_key < _semver_core(platform_compatibility.min_version):
            return False, (
                f"platform version {running} is below bundle's "
                f"min_version {platform_compatibility.min_version}"
            )

    if platform_compatibility.max_version is not None:
        if running_key > _semver_core(platform_compatibility.max_version):
            return False, (
                f"platform version {running} is above bundle's "
                f"max_version {platform_compatibility.max_version}"
            )

    tested_with = platform_compatibility.tested_with
    if tested_with and tested_with != running:
        return True, (
            f"platform version {running} is compatible but untested "
            f"(bundle tested_with={tested_with!r})"
        )

    return True, ""
