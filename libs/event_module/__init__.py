"""Event Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-31-v3-sccebm-program-plan.md SS1.1 and
docs/plans/2026-08-31-hubapi-node-to-quart-migration.md SS2: the Event
Module covers event + conference management -- OAuth calendar sync,
availability, booking pages, public booking, RSVPs, group scheduling
(``calendarController.js``) and ticketing/check-in/attendance
(``ticketController.js``). This package is Event's registration point for
the v3 Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`) -- see :mod:`event_module.features`.
Mirrors :mod:`bot_module`'s shape one-for-one.
"""
