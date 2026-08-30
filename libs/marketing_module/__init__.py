"""Marketing Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Modules``: Marketing
covers engagement (polls/forms), scheduling and cross-platform publishing,
seeded from ``core/engagement_module`` (~70% green-field, see the design
doc's ``Modules`` table). This package is Marketing's registration point
for the v3 Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`) -- see :mod:`marketing_module.features`.
Mirrors :mod:`bot_module` one-for-one; Social and Customer follow the same
shape as ``social_module`` and ``customer_module``.
"""
