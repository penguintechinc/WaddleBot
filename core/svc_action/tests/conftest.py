"""Pytest bootstrap for svc-action's tests.

svc_action isn't installed as a package (it's a standalone control-plane
directory run via `hypercorn app:app`, same shape as core/svc_streaming/
core/svc_presentation) -- so its own directory has to be put on sys.path
explicitly for `from app import app` / `import config` / `from services...`
to resolve.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Keep from_env() DB/Valkey defaults out of test collection -- individual
# tests construct their own ActionConfig/AsyncDAL/fakeredis instances
# rather than touching a real network resource at import time.
os.environ.setdefault("DB_TYPE", "sqlite")
