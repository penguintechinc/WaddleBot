"""Shared fixtures for core_platform_module tests.

Standalone copy of the import shim in `libs/flask_core/tests/conftest.py`
(deliberately not touching that shared file per this package's task scope):
`flask_core/__init__.py` eagerly imports the full service stack (pydal,
quart, authlib, ...), which this package's leaf-module imports
(`flask_core.app_manifest`, `.feature_contract`, `.feature_registry`,
`.app_registry`) have no business pulling in. Registers a lightweight
namespace-style `flask_core` package whose `__path__` points at the real
dir so submodule imports resolve directly, and puts `libs/` on `sys.path`
so `core_platform_module` itself (a sibling of `flask_core` under `libs/`,
not inside it) is importable the same way `bot_module` is in the shared
conftest. Runs before any test imports `flask_core.*` or
`core_platform_module.*`.
"""

from __future__ import annotations

import pathlib
import sys
import types

_LIBS_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
_FLASK_CORE_PKG_DIR = _LIBS_DIR / "flask_core" / "flask_core"

if "flask_core" not in sys.modules:
    _stub = types.ModuleType("flask_core")
    _stub.__path__ = [str(_FLASK_CORE_PKG_DIR)]
    sys.modules["flask_core"] = _stub

if str(_LIBS_DIR) not in sys.path:
    sys.path.insert(0, str(_LIBS_DIR))
