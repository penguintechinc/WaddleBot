"""
Test configuration for translate_interaction_module.

Sets up sys.path so tests can import from the module root (services/, proto/, etc.)
"""
import sys
import os

# Add module root so `from services.* import ...` works
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
# Add services/ so test files that import `translation_providers.*` directly work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
