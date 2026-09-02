"""Pytest bootstrap for workflow_core_module's tests.

workflow_core_module isn't installed as a package (it's a standalone
control-plane directory run via `hypercorn app:app`, same shape as
`core/svc_action`/`core/svc_streaming`) -- so its own directory has to be
put on sys.path explicitly for `from config import Config` / `from
controllers.workflow_api import ...` / `from services...` to resolve.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# `Config.SECRET_KEY = require_secret_key()` runs at import time
# (config.py module body) -- setting a real-looking value here keeps
# collection from depending on `require_secret_key`'s pytest-detection
# fallback being evaluated in exactly this process for every import order.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-workflow-core-module-tests")
