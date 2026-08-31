"""hub-api service layer -- business logic ported from Node's inline-in-controller SQL.

Node's `authController.js`/`identityController.js`/`passkeyController.js`/
`userManagementController.js`/`profileController.js` had no separate
service layer (queries lived directly in the Express controllers). This
package introduces one during the port -- routes (`blueprints/v1/*.py`)
stay thin (auth/tenant/DTO wiring only per `blueprints/v2/platform.py`'s
pattern), all DB/business logic lives here, off the event loop via
`flask_core.database.AsyncDAL`. See `hub_api/PORTING.md` for the recipe.

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
