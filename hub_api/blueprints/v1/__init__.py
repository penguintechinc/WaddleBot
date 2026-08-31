"""hub-api's v1 (frozen) port groups.

Each module in this package is one controller group, exposing a
module-level `BLUEPRINTS: list[Blueprint]` -- `routers/v1.py` auto-
discovers and mounts every one via `routers._discovery.discover_blueprints`.
Adding a group means dropping a new module here, never editing
`routers/v1.py` itself. See `blueprints/v1/auth.py` for the one example
today.
"""

from __future__ import annotations
