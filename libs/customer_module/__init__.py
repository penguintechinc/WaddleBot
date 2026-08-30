"""Customer Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Modules``: Customer is
100% green-field -- no pre-v3 code to convert, unlike Bot/Social/Marketing.
This package is Customer's registration point for the v3 Feature-contract
spine (:mod:`flask_core.feature_contract`, :mod:`flask_core.feature_registry`)
and its MVP Quart skeleton -- see :mod:`customer_module.features` and
:mod:`customer_module.app`. Mirrors :mod:`bot_module`'s shape one-for-one.
"""
