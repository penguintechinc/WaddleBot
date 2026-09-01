"""Streaming Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-31-v3-sccembs-program-plan.md SS1.1/SS4.3 and
docs/plans/2026-08-31-hubapi-node-to-quart-migration.md SS2: the Streaming
Module is ``svc-streaming`` + the hub-api control-plane portions --
live-stream listings (``streamController.js``), broadcast forward/record/
transcode config (``streamingController.js``), RTC/calls
(``callsController.js``), the music station
(``musicController.js``), and browser-source overlays
(``overlayController.js``). This package is Streaming's registration point
for the v3 Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`) -- see :mod:`streaming_module.features`.
Mirrors :mod:`bot_module`'s shape one-for-one.
"""
