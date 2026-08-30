"""Shared fixtures for social_module tests.

Self-contained sys.path shim -- deliberately not a shared fixture with
``libs/flask_core/tests/conftest.py`` (that file is not modified by this
task). Mirrors its "flask_core import shim" / "libs/ on sys.path" sections
exactly (same target directories, same reasoning), so
``social_module.features`` and ``flask_core.*`` submodules import without
pulling in ``flask_core``'s full ``__init__.py`` (pydal, quart, authlib, ...).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

# --- flask_core import shim (see libs/flask_core/tests/conftest.py) ---
# flask_core/__init__.py eagerly imports the full service stack (pydal,
# quart, authlib, ...). The leaf modules under test depend only on stdlib,
# so register a lightweight namespace-style `flask_core` package whose
# __path__ points at the real dir. Submodule imports then resolve directly
# without executing the heavy package __init__. Runs before any test
# imports flask_core.* or social_module.*.
_TESTS_DIR = Path(__file__).resolve().parent
_LIBS_DIR = _TESTS_DIR.parent.parent
_FLASK_CORE_PKG_DIR = _LIBS_DIR / "flask_core" / "flask_core"

if "flask_core" not in sys.modules:
    _stub = types.ModuleType("flask_core")
    _stub.__path__ = [str(_FLASK_CORE_PKG_DIR)]
    sys.modules["flask_core"] = _stub
# --- end flask_core shim ---

# --- libs/ on sys.path (module-package tests, e.g. social_module.features) ---
# social_module is a sibling of flask_core under libs/, not inside it, and
# registers its Feature contracts against flask_core.feature_registry -- so
# its tests need libs/ importable the same way flask_core's own tests do.
if str(_LIBS_DIR) not in sys.path:
    sys.path.insert(0, str(_LIBS_DIR))
# --- end libs/ path ---
