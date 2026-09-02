"""Shared pytest fixtures for this module's test suite.

Ensures MODULE_SECRET_KEY is set to a deterministic test value before
``config.Config`` is imported by any test module, so JWT signing/verification
in the auth interceptor tests is reproducible regardless of the local
environment (some modules default this to an empty string, which PyJWT
correctly refuses to sign with).
"""

import os

os.environ.setdefault(
    "MODULE_SECRET_KEY", "pytest-only-test-secret-do-not-use-in-production"
)
