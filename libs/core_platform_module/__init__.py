"""Core/Platform Module -- Feature contracts and default App bindings.

Per docs/plans/2026-08-26-v3-scbm-apps-design.md ``Modules``, the 4 product
Modules (Bot, Social, Marketing, Customer) are Helm-toggleable deployment
groupings. This package covers everything else: the Core/platform
capability namespaces that ship with every install regardless of which
product Modules are enabled -- ``analytics``, ``video_proxy``, ``auth``,
``compliance``, ``integrations``, ``tenancy`` (plus the reserved ``core``
namespace itself). Their Features still go through the same tier-gated
Feature-contract spine as product-Module Features (see
:mod:`flask_core.feature_contract`, :mod:`flask_core.feature_registry`) --
see :mod:`core_platform_module.features`. Mirrors :mod:`bot_module`'s shape
one-for-one, expanded to 7 namespaces instead of 1.
"""
