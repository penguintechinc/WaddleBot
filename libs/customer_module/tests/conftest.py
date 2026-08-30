"""Local pytest bootstrap for customer_module tests.

``customer_module`` registers against ``flask_core``'s Feature/App
registries the same way ``bot_module`` does (see
``libs/flask_core/tests/conftest.py`` for the sibling shim) -- this is
customer_module's own copy so its suite does not require touching the
shared flask_core conftest.py. Puts ``libs/flask_core`` (so ``flask_core``
resolves to its real package dir) and ``libs/`` (so ``customer_module``
resolves as a sibling package) on ``sys.path`` before any test imports
either one.
"""

from __future__ import annotations

import sys
from pathlib import Path

_TESTS_DIR = Path(__file__).resolve().parent
_CUSTOMER_MODULE_DIR = _TESTS_DIR.parent  # libs/customer_module
_LIBS_DIR = _CUSTOMER_MODULE_DIR.parent  # libs/
_FLASK_CORE_OUTER_DIR = _LIBS_DIR / "flask_core"  # contains the flask_core/ package

for _path in (_FLASK_CORE_OUTER_DIR, _LIBS_DIR):
    _str_path = str(_path)
    if _str_path not in sys.path:
        sys.path.insert(0, _str_path)
