"""Shared fixtures for streaming_module tests.

Self-contained sys.path shim -- mirrors ``libs/social_module/tests/
conftest.py``'s "flask_core import shim" / "libs/ on sys.path" sections
exactly (same target directories, same reasoning), so
``streaming_module.features`` and ``flask_core.*`` submodules import
without pulling in ``flask_core``'s full ``__init__.py`` (pydal, quart,
authlib, ...).
"""

from __future__ import annotations

import sys
import types
from pathlib import Path

# --- flask_core import shim (see libs/flask_core/tests/conftest.py) ---
_TESTS_DIR = Path(__file__).resolve().parent
_LIBS_DIR = _TESTS_DIR.parent.parent
_FLASK_CORE_PKG_DIR = _LIBS_DIR / "flask_core" / "flask_core"

if "flask_core" not in sys.modules:
    _stub = types.ModuleType("flask_core")
    _stub.__path__ = [str(_FLASK_CORE_PKG_DIR)]
    sys.modules["flask_core"] = _stub
# --- end flask_core shim ---

# --- libs/ on sys.path (module-package tests, e.g. streaming_module.features) ---
if str(_LIBS_DIR) not in sys.path:
    sys.path.insert(0, str(_LIBS_DIR))
# --- end libs/ path ---
