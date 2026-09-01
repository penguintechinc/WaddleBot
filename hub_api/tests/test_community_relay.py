"""`services/community_relay.py` -- direct unit tests for the mirror-group relay.

`relay_message`'s own group/target lookup queries use Postgres-only raw
SQL (`mgm.is_active = true` against a literal boolean, `mirror_group_id
= ANY($1)` array containment) that sqlite:memory cannot execute
correctly: pydal stores booleans as `'T'`/`'F'` TEXT on sqlite, so a raw
`= true` literal never matches (confirmed empirically -- `SELECT
is_active = true` returns `0` for a row inserted with `is_active=True`),
and sqlite has no `ANY()` function at all. Rather than adding more
documented skips (which would leave this file's *own* orchestration
logic -- direction filtering, `exclude_target_id`, hub-vs-platform
branching -- completely untested), `dal.executesql` is monkeypatched for
just those two queries so the rest of `relay_message`'s real code runs
unmocked against the real sqlite `dal` (ORM inserts/selects/updates
throughout `_dispatch_to_hub` work correctly against sqlite -- confirmed
separately -- it's specifically the two hand-written Postgres SQL
strings that don't). `_dispatch_to_hub`/`_dispatch_to_platform_bot` are
also exercised directly (no raw SQL in either), independent of
`relay_message`'s query layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from services.community_relay import _dispatch_to_hub, _dispatch_to_platform_bot, relay_message


def _seed_mirror_group(dal: Any, community_id: int) -> dict[str, int]:
    """Two mirror-group members: channel 1 (hub), channel 2 (discord), both `direction='both'`."""
    hub_server_id = dal.community_servers.insert(
        community_id=community_id,
        platform="hub",
        platform_server_id="hub-1",
        created_at=datetime.utcnow(),
    )
    discord_server_id = dal.community_servers.insert(
        community_id=community_id,
        platform="discord",
        platform_server_id="discord-srv-1",
        created_at=datetime.utcnow(),
    )
    hub_channel_row_id = dal.community_server_channels.insert(
        community_server_id=hub_server_id,
        platform_channel_id="hub-ch-1",
        platform_channel_name="general",
        channel_type="forum",
        created_at=datetime.utcnow(),
    )
    discord_channel_row_id = dal.community_server_channels.insert(
        community_server_id=discord_server_id,
        platform_channel_id="discord-123",
        platform_channel_name="announcements",
        channel_type="forum",
        created_at=datetime.utcnow(),
    )
    hub_channel_id = dal.hub_channels.insert(
        community_id=community_id,
        name="forum-general",
        channel_type="forum",
        community_server_channel_id=hub_channel_row_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    dal.commit()
    return {
        "hub_channel_row_id": hub_channel_row_id,
        "discord_channel_row_id": discord_channel_row_id,
        "hub_channel_id": hub_channel_id,
    }


def _mock_query_pair(
    monkeypatch: Any, dal: Any, *, groups_rows: list[Any], targets_rows: list[Any]
) -> None:
    """Stub `dal.executesql` for `relay_message`'s two calls only (group, then target lookup)."""
    calls = {"n": 0}
    real_executesql = dal.executesql

    def fake_executesql(sql: str, placeholders: Any = None, **kwargs: Any) -> list[Any]:
        calls["n"] += 1
        if calls["n"] == 1:
            return groups_rows
        if calls["n"] == 2:
            return targets_rows
        return real_executesql(sql, placeholders=placeholders, **kwargs)  # pragma: no cover

    monkeypatch.setattr(dal, "executesql", fake_executesql)


class TestNoGroups:
    async def test_no_matching_groups_returns_early(
        self, community_db: Any, monkeypatch: Any
    ) -> None:
        dal, community_id = community_db
        _mock_query_pair(monkeypatch, dal, groups_rows=[], targets_rows=[])
        await relay_message(
            dal,
            source_member_channel_id=999,
            platform="hub",
            channel_type="forum",
            content={},
            author={},
            message_type="forum_post",
        )
        assert dal(dal.hub_forum_posts.community_id == community_id).count() == 0


class TestRelayMessageOrchestration:
    """Exercises `relay_message`'s own loop body (target filtering, dispatch routing).

    with `dal.executesql` stubbed for its two Postgres-only queries -- see module docstring.
    """

    async def test_dispatches_to_hub_target(self, community_db: Any, monkeypatch: Any) -> None:
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        _mock_query_pair(
            monkeypatch,
            dal,
            groups_rows=[(1,)],
            targets_rows=[
                (
                    ids["hub_channel_row_id"],
                    "hub",
                    "hub-ch-1",
                    "general",
                    "both",
                    ids["hub_channel_id"],
                    community_id,
                )
            ],
        )

        await relay_message(
            dal,
            source_member_channel_id=ids["discord_channel_row_id"],
            platform="discord",
            channel_type="forum",
            content={"title": "Cross-posted", "body": "from discord", "tags": ["news"]},
            author={"platform": "discord", "username": "alice"},
            message_type="forum_post",
        )

        post = dal(dal.hub_forum_posts.hub_channel_id == ids["hub_channel_id"]).select().first()
        assert post is not None
        assert post.title == "Cross-posted"

    async def test_dispatches_to_platform_bot_target(
        self, community_db: Any, monkeypatch: Any
    ) -> None:
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        _mock_query_pair(
            monkeypatch,
            dal,
            groups_rows=[(1,)],
            targets_rows=[
                (
                    ids["discord_channel_row_id"],
                    "discord",
                    "discord-123",
                    "announcements",
                    "both",
                    None,
                    None,
                )
            ],
        )

        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False

        with patch("httpx.AsyncClient", return_value=mock_client):
            await relay_message(
                dal,
                source_member_channel_id=ids["hub_channel_row_id"],
                platform="hub",
                channel_type="forum",
                content={"title": "Hub announcement"},
                author={"platform": "hub", "username": "admin"},
                message_type="forum_post",
            )

        mock_client.post.assert_called_once()
        assert (
            mock_client.post.call_args.args[0] == "http://discord-bot-service:8080/internal/relay"
        )
        assert mock_client.post.call_args.kwargs["json"]["platformChannelId"] == "discord-123"

    async def test_exclude_target_id_skips_that_target(
        self, community_db: Any, monkeypatch: Any
    ) -> None:
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        _mock_query_pair(
            monkeypatch,
            dal,
            groups_rows=[(1,)],
            targets_rows=[
                (
                    ids["discord_channel_row_id"],
                    "discord",
                    "discord-123",
                    "announcements",
                    "both",
                    None,
                    None,
                )
            ],
        )

        with patch("httpx.AsyncClient") as mock_cls:
            await relay_message(
                dal,
                source_member_channel_id=ids["hub_channel_row_id"],
                platform="hub",
                channel_type="forum",
                content={"title": "x"},
                author={},
                message_type="forum_post",
                exclude_target_id=ids["discord_channel_row_id"],
            )
        mock_cls.assert_not_called()

    async def test_to_hub_direction_skips_target_when_source_is_hub(
        self, community_db: Any, monkeypatch: Any
    ) -> None:
        """`direction='to_hub'` means the target only *receives* from an external.

        platform -- a hub-originated message must skip it.
        """
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        _mock_query_pair(
            monkeypatch,
            dal,
            groups_rows=[(1,)],
            targets_rows=[
                (
                    ids["discord_channel_row_id"],
                    "discord",
                    "discord-123",
                    "announcements",
                    "to_hub",
                    None,
                    None,
                )
            ],
        )

        with patch("httpx.AsyncClient") as mock_cls:
            await relay_message(
                dal,
                source_member_channel_id=ids["hub_channel_row_id"],
                platform="hub",
                channel_type="forum",
                content={"title": "x"},
                author={},
                message_type="forum_post",
            )
        mock_cls.assert_not_called()

    async def test_from_hub_direction_skips_target_when_source_is_external(
        self, community_db: Any, monkeypatch: Any
    ) -> None:
        """`direction='from_hub'` means the target only *sends to* the platform --.

        an externally-originated message must skip it.
        """
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        _mock_query_pair(
            monkeypatch,
            dal,
            groups_rows=[(1,)],
            targets_rows=[
                (
                    ids["hub_channel_row_id"],
                    "hub",
                    "hub-ch-1",
                    "general",
                    "from_hub",
                    ids["hub_channel_id"],
                    community_id,
                )
            ],
        )

        await relay_message(
            dal,
            source_member_channel_id=ids["discord_channel_row_id"],
            platform="discord",
            channel_type="forum",
            content={"title": "should not post"},
            author={},
            message_type="forum_post",
        )
        assert dal(dal.hub_forum_posts.hub_channel_id == ids["hub_channel_id"]).count() == 0


class TestDispatchToHubDirect:
    """`_dispatch_to_hub` uses only ORM operations -- no raw-SQL portability concern here."""

    async def test_forum_post_writes_row(self, community_db: Any) -> None:
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        target = (0, "hub", "hub-ch-1", "general", "both", ids["hub_channel_id"], community_id)

        await _dispatch_to_hub(
            dal,
            target,
            {"title": "Direct post", "body": "b", "tags": ["x"]},
            {"platform": "discord", "username": "alice", "avatarUrl": "http://x/a.png"},
            "forum_post",
        )
        post = dal(dal.hub_forum_posts.hub_channel_id == ids["hub_channel_id"]).select().first()
        assert post is not None
        assert post.title == "Direct post"
        assert post.author_avatar_url == "http://x/a.png"

    async def test_forum_reply_bumps_reply_count(self, community_db: Any) -> None:
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        post_id = dal.hub_forum_posts.insert(
            hub_channel_id=ids["hub_channel_id"],
            community_id=community_id,
            title="Original",
            platform_thread_id="thread-1",
            reply_count=0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        dal.commit()
        target = (0, "hub", "hub-ch-1", "general", "both", ids["hub_channel_id"], community_id)

        await _dispatch_to_hub(
            dal,
            target,
            {"text": "reply text", "platformThreadId": "thread-1"},
            {"platform": "discord", "username": "bob"},
            "forum_reply",
        )
        reply = dal(dal.hub_forum_replies.post_id == post_id).select().first()
        assert reply is not None
        assert reply.content == "reply text"
        assert dal.hub_forum_posts[post_id].reply_count == 1

    async def test_forum_reply_no_matching_thread_is_a_noop(self, community_db: Any) -> None:
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        target = (0, "hub", "hub-ch-1", "general", "both", ids["hub_channel_id"], community_id)

        await _dispatch_to_hub(
            dal,
            target,
            {"text": "orphan", "platformThreadId": "no-such-thread"},
            {"platform": "discord", "username": "bob"},
            "forum_reply",
        )
        assert dal(dal.hub_forum_replies.content == "orphan").count() == 0

    async def test_message_type_message_is_a_noop(self, community_db: Any) -> None:
        """`message_type == "message"` requires the unmounted Socket.IO leg -- a no-op here."""
        dal, community_id = community_db
        ids = _seed_mirror_group(dal, community_id)
        target = (0, "hub", "hub-ch-1", "general", "both", ids["hub_channel_id"], community_id)

        await _dispatch_to_hub(dal, target, {"text": "chat"}, {"platform": "discord"}, "message")
        assert dal(dal.hub_forum_posts.community_id == community_id).count() == 0

    async def test_no_linked_hub_channel_is_a_noop(self, community_db: Any) -> None:
        """A mirror-group member with no linked `hub_channels` row (`hc.id IS NULL`)."""
        dal, _ = community_db
        target = (0, "hub", "x", "y", "both", None, None)
        await _dispatch_to_hub(dal, target, {"title": "x"}, {}, "forum_post")
        assert dal(dal.hub_forum_posts.id > 0).count() == 0


class TestDispatchToPlatformBotDirect:
    async def test_posts_to_configured_relay_url(self) -> None:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = False
        with patch("httpx.AsyncClient", return_value=mock_client):
            await _dispatch_to_platform_bot(
                "slack",
                (1, "slack", "slack-chan-1", "general", "both"),
                {"text": "hi"},
                {"username": "alice"},
                "message",
            )
        mock_client.post.assert_called_once()
        assert mock_client.post.call_args.args[0] == "http://slack-bot-service:8081/internal/relay"
        assert mock_client.post.call_args.kwargs["json"]["platformChannelId"] == "slack-chan-1"

    async def test_connection_error_is_swallowed(self) -> None:
        client = AsyncMock()
        client.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
        client.__aenter__.return_value = client
        client.__aexit__.return_value = False
        with patch("httpx.AsyncClient", return_value=client):
            # Must not raise -- fire-and-forget semantics.
            await _dispatch_to_platform_bot(
                "discord", (1, "discord", "chan-id", "chan-name", "both"), {}, {}, "message"
            )

    async def test_unknown_platform_is_a_noop(self) -> None:
        with patch("httpx.AsyncClient") as mock_cls:
            await _dispatch_to_platform_bot(
                "unknown-platform", (1, "unknown-platform", "x", "y", "both"), {}, {}, "message"
            )
        mock_cls.assert_not_called()


@pytest.mark.parametrize("platform_url_key", ["teams", "mattermost", "googlechat"])
async def test_remaining_relay_urls_are_reachable(platform_url_key: str) -> None:
    """Covers the `teams`/`mattermost`/`googlechat` branches of `_RELAY_URLS`."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    with patch("httpx.AsyncClient", return_value=mock_client):
        await _dispatch_to_platform_bot(
            platform_url_key, (1, platform_url_key, "x", "y", "both"), {}, {}, "message"
        )
    mock_client.post.assert_called_once()
