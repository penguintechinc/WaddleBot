"""hub-api service layer -- async I/O helpers ported controllers call into.

Per the migration plan's checklist (§4 step 3), each ported controller
group gets its own `services/<group>_*.py` module so blueprint handlers
stay thin (route/auth/DTO only) and I/O lives off the Quart handler body.
`event_calendar_proxy.py` is the first tenant: the Event module (calendar
+ ticketing) never touches Postgres directly from hub-api -- both Node
`calendarController`/`ticketController` proxy every request to the
`calendar-interaction` service, so hub-api's own service layer for this
group is an async HTTP proxy client, not a DAL wrapper.
"""

from __future__ import annotations
