"""Unit tests for `services.distribution_service` -- the service-layer stage guard.

The blueprint (`blueprints/v1/distribution.py`) already validates `stage`
before ever calling `list_bundles_for_stage`, so the service's own
`InvalidStageError` defensive check (`stage not in BUNDLE_STAGES`) needs a
direct unit test to exercise it -- defense in depth for any future caller
that skips the blueprint's own validation.
"""

from __future__ import annotations

import pytest

from services.distribution_service import BUNDLE_STAGES, InvalidStageError, list_bundles_for_stage


class TestInvalidStage:
    async def test_raises_before_touching_dal(self) -> None:
        """Raises on the bad `stage` value alone -- never dereferences `async_dal`/`dal`."""
        with pytest.raises(InvalidStageError, match="invalid stage"):
            await list_bundles_for_stage(
                None, None, tenant_id=1, community_id=None, stage="not-a-real-stage"
            )

    @pytest.mark.parametrize("stage", BUNDLE_STAGES)
    async def test_valid_stages_do_not_raise_invalid_stage_error(self, stage: str) -> None:
        """Each real stage passes the guard (still needs a real dal -- caught downstream)."""
        with pytest.raises(AttributeError):  # None.app_activations -- proves the guard passed
            await list_bundles_for_stage(None, None, tenant_id=1, community_id=1, stage=stage)
