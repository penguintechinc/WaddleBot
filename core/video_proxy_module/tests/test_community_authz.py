"""`services/community_authz.py` -- BOLA/IDOR fix (A01, deferred from gh security PR #260).

Fail-first proof (executed, not narrated): with `require_member`'s body
temporarily replaced with `return None` (no check at all -- the pre-fix
shape), `test_non_member_fails_require_member` went green -> red as
expected (no exception raised for a non-member); reverted after confirming.
"""

from __future__ import annotations

from typing import Any

import pytest
from pydal import DAL

from services.community_authz import (
    CommunityAccessError,
    bind_shared_read_tables,
    extract_user_id,
    require_admin,
    require_member,
)


@pytest.fixture
def db() -> Any:
    dal = DAL("sqlite:memory")
    bind_shared_read_tables(dal, migrate=True)
    yield dal
    dal.close()


@pytest.fixture
def seeded(db: Any) -> dict[str, int]:
    community_id = db.communities.insert(tenant_id=1)
    other_community_id = db.communities.insert(tenant_id=1)
    db.community_members.insert(
        community_id=community_id, user_id="1", role="community-admin", is_active=True
    )
    db.community_members.insert(
        community_id=community_id, user_id="2", role="member", is_active=True
    )
    db.community_members.insert(
        community_id=community_id, user_id="3", role="member", is_active=False
    )
    db.commit()
    return {"community_id": community_id, "other_community_id": other_community_id}


class TestRequireMember:
    def test_active_member_passes(self, db: Any, seeded: dict[str, int]) -> None:
        require_member(db, community_id=seeded["community_id"], user_id="1")
        require_member(db, community_id=seeded["community_id"], user_id="2")

    def test_non_member_fails_require_member(self, db: Any, seeded: dict[str, int]) -> None:
        with pytest.raises(CommunityAccessError):
            require_member(db, community_id=seeded["community_id"], user_id="999")

    def test_inactive_member_fails(self, db: Any, seeded: dict[str, int]) -> None:
        with pytest.raises(CommunityAccessError):
            require_member(db, community_id=seeded["community_id"], user_id="3")

    def test_member_of_a_different_community_fails(self, db: Any, seeded: dict[str, int]) -> None:
        with pytest.raises(CommunityAccessError):
            require_member(db, community_id=seeded["other_community_id"], user_id="1")


class TestRequireAdmin:
    def test_admin_passes(self, db: Any, seeded: dict[str, int]) -> None:
        require_admin(db, community_id=seeded["community_id"], user_id="1")

    def test_plain_member_fails_require_admin(self, db: Any, seeded: dict[str, int]) -> None:
        with pytest.raises(CommunityAccessError):
            require_admin(db, community_id=seeded["community_id"], user_id="2")


class TestExtractUserId:
    def test_sub_claim(self) -> None:
        assert extract_user_id({"sub": "42"}) == "42"

    def test_legacy_user_id_claim(self) -> None:
        assert extract_user_id({"user_id": "42"}) == "42"

    def test_missing_both_raises(self) -> None:
        with pytest.raises(CommunityAccessError):
            extract_user_id({})
