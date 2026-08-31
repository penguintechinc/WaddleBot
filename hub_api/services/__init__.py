"""hub-api service layer -- business logic ported from Node's inline-in-controller SQL.

Node's `authController.js`/`identityController.js`/`passkeyController.js`/
`userManagementController.js`/`profileController.js` had no separate
service layer (queries lived directly in the Express controllers). This
package introduces one during the port -- routes (`blueprints/v1/*.py`)
stay thin (auth/tenant/DTO wiring only per `blueprints/v2/platform.py`'s
pattern), all DB/business logic lives here, off the event loop via
`flask_core.database.AsyncDAL`. See `hub_api/PORTING.md` for the recipe.
"""

from __future__ import annotations
