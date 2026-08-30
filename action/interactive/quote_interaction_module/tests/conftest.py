"""Test configuration for quote_interaction_module.

Sets up sys.path so tests can import from the module root (services/,
config.py, app.py) the same way app.py does at runtime -- mirrors
action/interactive/welcome_interaction_module/tests/conftest.py.
"""
import os
import sys

# Pre-import the real, pip-installed flask_core (from this venv's
# site-packages) into sys.modules BEFORE app.py's own module-level
# `sys.path.insert(0, '<repo>/libs')` runs. That insert points at
# `libs/flask_core` (the *distribution* root, containing setup.py --
# not the `flask_core` package dir one level deeper), which Python
# happily treats as a namespace package and, being at sys.path[0],
# shadows the correct one. Pre-populating sys.modules sidesteps that
# pre-existing app.py path bug (unrelated to this suite) without
# patching production code just to make it importable under pytest.
import flask_core  # noqa: F401

# Add module root so `from app import app`, `import config`, and
# `from services.* import ...` all work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
