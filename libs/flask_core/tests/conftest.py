"""
pytest bootstrap for the flask_core test suite.

``flask_core/__init__.py`` eagerly imports the full service stack (pydal,
quart, authlib, ...). ``workload_identity`` itself depends only on the
standard library, so to unit-test it without provisioning every optional
runtime dependency we register a lightweight ``flask_core`` package stub whose
``__path__`` points at the real package directory. ``from
flask_core.workload_identity import ...`` then resolves the submodule directly
without executing the heavy package ``__init__``. In a fully provisioned
environment (all requirements installed) the normal import path works
unchanged; this shim only avoids unrelated missing-dependency noise here.
"""

import pathlib
import sys
import types

_PKG_DIR = pathlib.Path(__file__).resolve().parent.parent / "flask_core"

if "flask_core" not in sys.modules:
    _stub = types.ModuleType("flask_core")
    _stub.__path__ = [str(_PKG_DIR)]  # make it a namespace-style package
    sys.modules["flask_core"] = _stub
