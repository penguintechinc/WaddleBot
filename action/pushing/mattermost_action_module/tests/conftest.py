"""Shared pytest fixtures for this module's test suite.

Ensures JWT_SECRET is set to a deterministic test value before
``config.Config`` is imported by any test module, so JWT signing/verification
in the auth interceptor tests is reproducible regardless of the local
environment.
"""

import os

os.environ.setdefault(
    "JWT_SECRET", "pytest-only-test-secret-do-not-use-in-production"
)
