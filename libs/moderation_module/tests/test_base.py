"""Unit tests for `moderation_module.base` -- `Classification` and `ClassificationProvider`."""

from __future__ import annotations

import pytest

from moderation_module.base import Classification, ClassificationProvider


class TestClassification:
    def test_valid_construction(self) -> None:
        c = Classification(category="hate_speech", confidence=0.9, severity="high")
        assert c.category == "hate_speech"
        assert c.confidence == 0.9
        assert c.severity == "high"

    @pytest.mark.parametrize("bad_confidence", [-0.01, 1.01, -5.0, 100.0])
    def test_out_of_range_confidence_rejected(self, bad_confidence: float) -> None:
        with pytest.raises(ValueError, match="confidence"):
            Classification(category="hate_speech", confidence=bad_confidence, severity="low")

    def test_unknown_severity_rejected(self) -> None:
        with pytest.raises(ValueError, match="severity"):
            Classification(category="hate_speech", confidence=0.5, severity="critical")

    def test_is_frozen(self) -> None:
        c = Classification(category="slurs", confidence=0.7, severity="medium")
        with pytest.raises(AttributeError):
            c.confidence = 0.1  # type: ignore[misc]

    def test_boundary_confidences_accepted(self) -> None:
        Classification(category="hate_speech", confidence=0.0, severity="low")
        Classification(category="hate_speech", confidence=1.0, severity="high")


class TestClassificationProvider:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            ClassificationProvider()  # type: ignore[abstract]

    async def test_subclass_must_implement_classify(self) -> None:
        class Incomplete(ClassificationProvider):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    async def test_concrete_subclass_works(self) -> None:
        class Always(ClassificationProvider):
            async def classify(
                self,
                message: str,
                enabled_categories: set[str],
                *,
                tenant_id: int,
                community_id: int,
            ) -> Classification | None:
                return Classification(category="hate_speech", confidence=0.9, severity="high")

        result = await Always().classify("x", {"hate_speech"}, tenant_id=1, community_id=1)
        assert result is not None
        assert result.category == "hate_speech"
