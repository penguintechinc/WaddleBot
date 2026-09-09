"""Community Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-31-v3-sccebm-program-plan.md SS1.1 and
docs/plans/2026-08-31-hubapi-node-to-quart-migration.md SS2: the Community
Module is the *management/engagement* product module -- forum, chat,
virtual stages, polls, announcements, activity, loyalty, inventory,
raffles -- distinct from the community **entity** (teams/OUs in the
``global -> tenant -> community`` scope ladder), which is Core, not this
module. This package is Community's registration point for the v3
Feature-contract spine (:mod:`flask_core.feature_contract`,
:mod:`flask_core.feature_registry`) -- see :mod:`community_module.features`.
Mirrors :mod:`bot_module`/:mod:`social_module`'s shape one-for-one, per
program plan SS9 P4 ("map 44 controllers -> default App Bundles per
module").
"""
