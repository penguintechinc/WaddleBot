"""Test configuration for shoutout_interaction_module.

Sets up sys.path so tests can import from the module root (services/,
config.py, app.py) the same way app.py does at runtime -- mirrors
action/interactive/welcome_interaction_module/tests/conftest.py.
"""
import os
import sys

# Add module root so `from app import app`, `import config`, and
# `from services.* import ...` all work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
