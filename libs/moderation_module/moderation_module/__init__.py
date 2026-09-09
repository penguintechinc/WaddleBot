"""moderation_module -- pluggable content-moderation classification.

Per docs/plans/2026-09-08-content-moderation-design.md SS5/SS6: this
package holds the `ClassificationProvider` contract (`base.py`) and its
Basic-tier implementation (`providers/local_ollama.py`'s
`LocalOllamaClassifier`, local Ollama running a ShieldGemma model). It is
the classifier slice only -- the svc-process moderation stage gate (SS4)
and reputation-hit wiring (SS2, blocked on #299) are separate, out-of-
scope work; nothing here imports `core.svc_process` or
`core.reputation_module`.

Mirrors `libs/waddle_transports`' shape (pluggable-implementation package
with its own `pyproject.toml`/`requirements.in`, installed as a real pip
package rather than resolved via the feature-contract modules'
`libs/`-on-`sys.path` convention) since, like transports, this package's
whole point is several interchangeable implementations behind one
contract -- not a `features.py` feature-flag registration point like
`community_module`/`bot_module`/etc.
"""

from __future__ import annotations

from moderation_module.base import Classification, ClassificationProvider
from moderation_module.providers.local_ollama import (
    ALTERNATE_MODEL,
    BASIC_CATEGORY_POLICIES,
    DEFAULT_MODEL,
    LocalOllamaClassifier,
    OllamaConfig,
)

__all__ = [
    "ALTERNATE_MODEL",
    "BASIC_CATEGORY_POLICIES",
    "DEFAULT_MODEL",
    "Classification",
    "ClassificationProvider",
    "LocalOllamaClassifier",
    "OllamaConfig",
]
