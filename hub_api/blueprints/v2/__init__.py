"""hub-api's v2 (additive, bundle-oriented) port groups.

Each module in this package is one `{module}/{surface}/{app_bundle}`
group, exposing a module-level `BLUEPRINTS: list[Blueprint]` (each
blueprint's `url_prefix` already the full `/api/v2/...` path) --
`routers/v2.py` auto-discovers and mounts every one via
`routers._discovery.discover_blueprints`. Adding a group means dropping a
new module here, never editing `routers/v2.py` itself. See
`blueprints/v2/platform.py` for the copy-me exemplar.
"""

from __future__ import annotations
