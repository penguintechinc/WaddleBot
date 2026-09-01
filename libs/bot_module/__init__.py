"""Bot Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Modules``: Bot covers
triggers, actions, interactions and command dispatch, seeded from
``trigger/receiver/*``, ``action/pushing/*`` and ``action/interactive/*``.
This package is Bot's registration point for the v3 Feature-contract spine
(:mod:`flask_core.feature_contract`, :mod:`flask_core.feature_registry`) --
see :mod:`bot_module.features`. Social, Marketing and Customer mirror this
package's shape one-for-one as ``social_module``, ``marketing_module`` and
``customer_module``.
"""
