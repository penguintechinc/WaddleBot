"""Local fixtures for marketing_module tests.

Deliberately separate from libs/flask_core/tests/conftest.py (not touched by
this module) -- performs the equivalent libs/ sys.path setup for
``marketing_module.features`` plus one extra piece the shared conftest
doesn't need: a fixture that imports core/engagement_module/app.py with
pydal.DAL mocked out, so the worked-gate test can exercise the real
``create_poll`` handler over HTTP without a live Postgres connection
(PyDAL's postgres adapter connects eagerly at ``DAL(...)`` construction,
which is module-level code in app.py).
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

# --- libs/ on sys.path, so `import marketing_module.features` resolves
# the same way flask_core/tests/conftest.py does for bot_module.
_LIBS_DIR = Path(__file__).resolve().parents[2]
if str(_LIBS_DIR) not in sys.path:
    sys.path.insert(0, str(_LIBS_DIR))

# --- core/engagement_module/ on sys.path, so app.py's own `from config
# import Config` (a plain top-level import, not a relative one) resolves.
_ENGAGEMENT_DIR = _LIBS_DIR.parent / "core" / "engagement_module"
if str(_ENGAGEMENT_DIR) not in sys.path:
    sys.path.insert(0, str(_ENGAGEMENT_DIR))


@pytest.fixture
def engagement_app() -> Iterator[ModuleType]:
    """A fresh import of core/engagement_module/app.py, DAL mocked.

    ``pydal.DAL`` is patched before import so the module-level
    ``db = DAL(config.DATABASE_URL, ...)`` call in app.py never attempts a
    real Postgres connection -- ``app.db`` ends up a bare ``MagicMock``,
    exercised directly by tests via call-count assertions rather than real
    query results.
    """
    sys.modules.pop("app", None)
    with patch("pydal.DAL") as mock_dal_cls:
        mock_dal_cls.return_value = MagicMock()
        import app as engagement_app_module
    yield engagement_app_module
    sys.modules.pop("app", None)
