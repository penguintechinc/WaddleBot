"""Pytest configuration for the unified_music_module provider tests.

Provider modules (`youtube_provider.py`, `spotify_provider.py`, ...) use
package-relative imports (`from .base_provider import ...`), so pytest must
load them as part of the `providers` package rather than as bare top-level
modules -- otherwise the relative import fails with "attempted relative
import with no known parent package". Inserting the package's parent
directory onto `sys.path` lets test modules do
`from providers.<module> import ...` and have it resolve correctly.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
