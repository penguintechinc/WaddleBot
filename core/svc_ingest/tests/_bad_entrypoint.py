"""Test-only ingest entrypoint that violates the `PlatformEvent` return contract.

Referenced by `test_runner.py` to exercise `IngestRunner`'s `EnvelopeError`
guard when a bundle's `normalize()` returns something other than a
`flask_core.PlatformEvent` -- ALPHA has no legacy-shape tolerance, so this
must be refused, not silently coerced.
"""

from __future__ import annotations

from typing import Any


async def normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Deliberately return a bare dict instead of a `PlatformEvent`."""
    return {"not": "a PlatformEvent"}
