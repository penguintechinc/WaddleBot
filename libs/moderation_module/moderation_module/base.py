"""`ClassificationProvider` contract and its `Classification` result shape.

Per docs/plans/2026-09-08-content-moderation-design.md SS5: every content-
moderation classifier (`providers/local_ollama.py`'s `LocalOllamaClassifier`
today, a future `WaddleAIClassifier` for Advanced/Security packs) implements
this one interface, so the svc-process moderation gate (out of scope here --
see SS4) never branches on which provider is wired in. `enabled_categories`
is caller-supplied per (tenant, community) -- a provider only ever spends
work on categories the caller actually asked for, never the full set it
knows how to classify.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

#: `Classification.severity` is constrained to exactly these three values --
#: see `Classification.__post_init__`.
_VALID_SEVERITIES = frozenset({"low", "medium", "high"})


@dataclass(slots=True, frozen=True)
class Classification:
    """One matched moderation category for a single message.

    Frozen + slotted: a classifier's return value is handed straight to the
    (not-yet-built) svc-process gate for a reputation-hit decision, never
    mutated in place. `confidence` is a model-specific calibrated
    probability in `[0.0, 1.0]` that the message violates `category`'s
    policy; `severity` is a coarse bucket a caller can act on without
    needing to know each provider's own confidence scale.
    """

    category: str
    confidence: float
    severity: str

    def __post_init__(self) -> None:
        """Reject an out-of-range confidence or an unrecognized severity bucket."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence!r}")
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(
                f"severity must be one of {sorted(_VALID_SEVERITIES)}, got {self.severity!r}"
            )


class ClassificationProvider(ABC):
    """Classify one inbound chat message for harmful content.

    Implementations are pluggable (local Ollama vs. WaddleAI, per SS5/SS6) --
    the caller (the svc-process moderation gate) is written once against
    this ABC and never imports a concrete provider directly.
    """

    @abstractmethod
    async def classify(
        self,
        message: str,
        enabled_categories: set[str],
        *,
        tenant_id: int,
        community_id: int,
    ) -> Classification | None:
        """Classify `message` against `enabled_categories` only.

        `tenant_id`/`community_id` identify the caller for provider-side
        logging/metering (e.g. a WaddleAI-backed provider's per-tenant
        quota) -- never used to widen or narrow `enabled_categories`
        itself, that decision belongs entirely to the caller.

        Returns the single highest-confidence matched `Classification`, or
        `None` if no enabled category matched. A category that was checked
        and did not match is not an error and is not reported -- only a
        match is ever returned.
        """
        raise NotImplementedError
