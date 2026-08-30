"""Social Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Modules``: Social covers
community engagement -- polls, presence, communities, aliases, quotes,
browser sources, RTC and AI-assisted welcomes -- seeded from
``core/community_module``, ``core/module_rtc``,
``core/browser_source_core_module``, ``libs/presence`` and
``action/interactive/{alias,quote,welcome}_interaction_module``. This
package is Social's registration point for the v3 Feature-contract spine
(:mod:`flask_core.feature_contract`, :mod:`flask_core.feature_registry`) --
see :mod:`social_module.features`. Mirrors :mod:`bot_module`'s shape
one-for-one, as Marketing and Customer will as ``marketing_module`` and
``customer_module``.
"""
