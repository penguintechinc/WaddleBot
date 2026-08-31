"""hub-api service layer -- async business logic behind the v1/v2 blueprints.

Each ``community_*.py`` module here is the service layer for one ported
Community-module (engagement) controller (docs/plans/2026-08-31-hubapi-
node-to-quart-migration.md M6): pydal/HTTP-proxy I/O the corresponding
``blueprints/v1/community_*.py`` blueprint calls into. Kept separate from
the blueprint modules per the migration plan's checklist (`Service ->
async service fn (I/O off the event loop)`), even though this monorepo's
established convention (`services/core-community/app.py`, `blueprints/v2/
platform.py`) calls the raw synchronous `pydal` `dal` directly rather than
wrapping every query in `asyncio.to_thread` -- see `community_common.py`'s
docstring for why that established pattern is followed here too.
"""

from __future__ import annotations
