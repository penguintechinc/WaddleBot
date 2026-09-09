"""Regression coverage: `ReputationService`'s `self.logger.audit(...)` calls vs the REAL signature.

`flask_core.logging_config.AAALogger.audit()`'s real signature is
`(action, user, community, result, **kwargs)` -- `user`/`community`/
`result` are all REQUIRED POSITIONAL-OR-KEYWORD params. Both `adjust()`'s
and `set_reputation()`'s `self.logger.audit(...)` call sites previously
supplied only `action` plus a pile of unrelated keyword args
(`community_id=`, `user_id=`, `score_before=`, ...), never `user`/
`community`/`result` themselves -- a `TypeError: audit() missing 3 required
positional arguments: 'user', 'community', and 'result'`, raised on every
successful adjustment and caught by `adjust()`/`set_reputation()`'s own
broad `except Exception`, silently turning a real, already-committed DB
write into `AdjustmentResult(success=False, error=...)`.

`core/svc_process/services/reputation_gate_client.py`'s prior vendored-
import bridge worked around exactly this by swapping in a `_
PermissiveAuditLogger` shim that accepted any call shape -- masking the
bug for every caller going through that bridge. Now that svc-process calls
`reputation_module` over real HTTP (never importing this module's code
directly), nothing shims around a broken `.audit()` call anymore, so this
test exercises the REAL `AAALogger` (via `flask_core.setup_aaa_logging`,
never a `NullLogger`/permissive stand-in) to prove the call sites actually
match its signature and `result.success` reports the real outcome.

A fake DAL (never a live Postgres) keeps this test always-running, not
skip-conditional like `test_reputation_tables.py`'s real-Postgres
integration suite -- it must run, and fail, in every environment.
"""

from __future__ import annotations

from typing import Any

from flask_core import setup_aaa_logging

from services.reputation_service import ReputationService
from services.weight_manager import WeightManager


class _FakeReputationDal:
    """Minimal sync pydal-style stand-in: every SELECT empty (new member), every write a no-op."""

    def executesql(self, sql: str, params: list[Any] | None = None) -> list[Any]:
        return []

    def commit(self) -> None:
        return None


class _ExistingMemberDal(_FakeReputationDal):
    """Like `_FakeReputationDal`, but reports one existing `community_members` row.

    Matches `set_reputation()`'s own lookup query so its "user not found"
    early-return branch is skipped and the real audit call site is reached.
    """

    def executesql(self, sql: str, params: list[Any] | None = None) -> list[Any]:
        if "SELECT reputation FROM community_members" in sql:
            return [(600,)]
        return super().executesql(sql, params)


class TestAdjustAuditCallMatchesRealSignature:
    async def test_adjust_success_does_not_raise_through_real_aaa_logger(
        self, tmp_path: Any
    ) -> None:
        dal = _FakeReputationDal()
        logger = setup_aaa_logging("reputation-module-test", "0.0.0", log_dir=str(tmp_path))
        weight_manager = WeightManager(dal, logger)
        service = ReputationService(dal, weight_manager, logger)

        result = await service.adjust(
            community_id=42,
            user_id=None,
            event_type="warn",
            platform="twitch",
            platform_user_id="u-1",
            reason="test moderation hit",
        )

        # Pre-fix, the mismatched `.audit()` call raised a TypeError inside
        # the try block, caught by `adjust()`'s own broad `except Exception`
        # -- `result.success` silently flipped to `False` despite the DB
        # write itself having already succeeded.
        assert result.success is True, result.error
        assert result.error is None
        assert result.score_change == -25.0
        assert result.score_before == 600
        assert result.score_after == 575

    async def test_adjust_with_linked_user_does_not_raise_through_real_aaa_logger(
        self, tmp_path: Any
    ) -> None:
        """Covers the `user=str(user_id)` branch (hub-linked user) of the audit fix."""
        dal = _FakeReputationDal()
        logger = setup_aaa_logging("reputation-module-test", "0.0.0", log_dir=str(tmp_path))
        weight_manager = WeightManager(dal, logger)
        service = ReputationService(dal, weight_manager, logger)

        result = await service.adjust(
            community_id=42,
            user_id=7,
            event_type="follow",
            platform="discord",
            platform_user_id="p-1",
        )

        assert result.success is True, result.error
        assert result.error is None


class TestSetReputationAuditCallMatchesRealSignature:
    async def test_set_reputation_success_does_not_raise_through_real_aaa_logger(
        self, tmp_path: Any
    ) -> None:
        dal = _ExistingMemberDal()
        logger = setup_aaa_logging("reputation-module-test", "0.0.0", log_dir=str(tmp_path))
        weight_manager = WeightManager(dal, logger)
        service = ReputationService(dal, weight_manager, logger)

        result = await service.set_reputation(
            community_id=42,
            user_id=7,
            score=650,
            reason="admin correction",
            admin_id=1,
        )

        # Pre-fix: same TypeError/broad-except failure mode as adjust()'s
        # own audit call.
        assert result.success is True, result.error
        assert result.error is None
        assert result.score_before == 600
        assert result.score_after == 650
        assert result.score_change == 50
