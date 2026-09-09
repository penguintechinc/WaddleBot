"""Tests for `bundles.community_polls_process.transform`."""

from __future__ import annotations

from typing import Any

import pytest
from flask_core import (
    PlatformEvent,
    bundle_context,
    reset_bundle_dal_for_tests,
    set_bundle_dal,
)

from bundles.community_polls_process import (
    _parse_quoted_args,
    transform,
)


class _FakeDal:
    """In-memory stand-in for `AsyncDAL` -- implements `.execute()` for poll queries."""

    def __init__(self) -> None:
        self._polls: dict[int, dict[str, Any]] = {}
        self._options: dict[int, dict[str, Any]] = {}
        self._votes: list[dict[str, Any]] = []
        self._next_poll_id: int = 1
        self._next_option_id: int = 1

    async def execute(self, sql: str, params: list[Any]) -> list[dict[str, Any]]:
        """Execute a mock query and return results based on stored data."""
        # Map SQL pattern to handler for clarity
        sql_lower = sql.lower()

        if "insert into community_polls" in sql_lower and "returning" in sql_lower:
            poll_id = self._next_poll_id
            self._next_poll_id += 1
            self._polls[poll_id] = {
                "id": poll_id,
                "community_id": params[0],
                "created_by": params[1],
                "title": params[2],
                "is_active": True,
            }
            return [{"id": poll_id}]
        elif "insert into poll_options" in sql_lower:
            option_id = self._next_option_id
            self._next_option_id += 1
            self._options[option_id] = {
                "id": option_id,
                "poll_id": params[0],
                "option_text": params[1],
                "sort_order": params[2],
            }
            return []
        elif (
            "select id, title from community_polls" in sql_lower
            and "is_active = true" in sql_lower
            and "where id = $1" in sql_lower
            and "community_id = $2" in sql_lower
        ):
            # Single poll by ID check with active filter and community scope
            poll_id = params[0]
            community_id = params[1]
            if poll_id in self._polls:
                poll = self._polls[poll_id]
                if poll["is_active"] and poll["community_id"] == community_id:
                    return [{"id": poll["id"], "title": poll["title"]}]
            return []
        elif "select id from poll_options where poll_id" in sql_lower:
            poll_id = params[0]
            return [
                {"id": opt_id, "option_text": opt["option_text"]}
                for opt_id, opt in self._options.items()
                if opt["poll_id"] == poll_id
            ]
        elif (
            "update community_polls set is_active = false" in sql_lower
            and "community_id = $2" in sql_lower
        ):
            poll_id = params[0]
            community_id = params[1]
            if poll_id in self._polls and self._polls[poll_id]["community_id"] == community_id:
                self._polls[poll_id]["is_active"] = False
            return []
        elif (
            "select id, title, is_active from community_polls where id = $1 and community_id = $2"
        ) in sql_lower:
            # View poll scoped to community
            poll_id = params[0]
            community_id = params[1]
            if poll_id in self._polls:
                poll = self._polls[poll_id]
                if poll["community_id"] == community_id:
                    return [
                        {
                            "id": poll["id"],
                            "title": poll["title"],
                            "is_active": poll["is_active"],
                        }
                    ]
            return []
        elif (
            "select id, title from community_polls where id = $1 and community_id = $2"
        ) in sql_lower:
            # Close/general poll lookup scoped to community
            poll_id = params[0]
            community_id = params[1]
            if poll_id in self._polls:
                poll = self._polls[poll_id]
                if poll["community_id"] == community_id:
                    return [{"id": poll["id"], "title": poll["title"]}]
            return []
        elif "select id, title from community_polls where id = $1" in sql_lower:
            poll_id = params[0]
            if poll_id in self._polls:
                poll = self._polls[poll_id]
                return [{"id": poll["id"], "title": poll["title"]}]
            return []
        elif "select po.option_text, count(pv.id)" in sql_lower and "group by" in sql_lower:
            poll_id = params[0]
            result = []
            for opt_id, opt in self._options.items():
                if opt["poll_id"] == poll_id:
                    vote_count = sum(1 for v in self._votes if v["option_id"] == opt_id)
                    result.append({"option_text": opt["option_text"], "vote_count": vote_count})
            return result
        elif (
            "select id, title from community_polls" in sql_lower
            and "where community_id = $1 and is_active = true" in sql_lower
        ):
            # List active polls in community
            community_id = params[0]
            return [
                {"id": poll["id"], "title": poll["title"]}
                for poll in self._polls.values()
                if poll["community_id"] == community_id and poll["is_active"]
            ]
        elif "select po.id, po.option_text, count(pv.id)" in sql_lower:
            poll_id = params[0]
            result = []
            for opt_id, opt in self._options.items():
                if opt["poll_id"] == poll_id:
                    vote_count = sum(1 for v in self._votes if v["option_id"] == opt_id)
                    result.append(
                        {
                            "id": opt_id,
                            "option_text": opt["option_text"],
                            "vote_count": vote_count,
                        }
                    )
            return result
        elif "insert into poll_votes" in sql_lower:
            self._votes.append(
                {
                    "poll_id": params[0],
                    "option_id": params[1],
                    "user_id": params[2],
                }
            )
            return []
        return []


@pytest.fixture(autouse=True)
def _dal() -> Any:
    """Set up and tear down fake DAL for each test."""
    fake = _FakeDal()
    set_bundle_dal(fake)
    yield fake
    reset_bundle_dal_for_tests()


def _event(text: str, actor: str = "penguin") -> PlatformEvent:
    """Create a test PlatformEvent with the given text."""
    payload: dict = {"text": text, "channel_id": "chan-1"}
    return PlatformEvent(
        platform="discord",
        event_type="message",
        actor=actor,
        payload=payload,
        occurred_at="2026-01-01T00:00:00+00:00",
    )


class TestTransform:
    """Tests for the main transform entrypoint."""

    async def test_non_poll_command_returns_none(self, _dal: _FakeDal) -> None:
        """Ordinary chatter should return None."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("just chatting"))
        assert result is None

    async def test_poll_command_no_subcommand_returns_help(self, _dal: _FakeDal) -> None:
        """Bare `!poll` with no subcommand returns help."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll"))
        assert result is not None
        assert result.payload["text"]
        assert "create" in result.payload["text"].lower()
        assert "list" in result.payload["text"].lower()

    async def test_poll_list_returns_active_polls(self, _dal: _FakeDal) -> None:
        """!poll list returns active polls for the community."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Test Poll",
            "is_active": True,
        }
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll list"))
        assert result is not None
        assert "Test Poll" in result.payload["text"]

    async def test_poll_create_missing_args(self, _dal: _FakeDal) -> None:
        """!poll create without arguments returns usage."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll create"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_poll_create_insufficient_options(self, _dal: _FakeDal) -> None:
        """!poll create with only title and one option returns error."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event('!poll create "My Poll" "Option1"'))
        assert result is not None
        assert "at least 2 options" in result.payload["text"].lower()

    async def test_poll_create_success(self, _dal: _FakeDal) -> None:
        """!poll create with valid args creates a poll."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event('!poll create "My Poll" "Opt1" "Opt2"'))
        assert result is not None
        assert "Poll created" in result.payload["text"]
        assert "My Poll" in result.payload["text"]

    async def test_poll_vote_missing_args(self, _dal: _FakeDal) -> None:
        """!poll vote without arguments returns usage."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_poll_vote_insufficient_args(self, _dal: _FakeDal) -> None:
        """!poll vote with only poll_id returns error."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 123"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_poll_vote_non_numeric_poll_id(self, _dal: _FakeDal) -> None:
        """!poll vote with non-numeric poll_id returns error."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote abc 1"))
        assert result is not None
        assert "numeric" in result.payload["text"].lower()

    async def test_poll_close_missing_args(self, _dal: _FakeDal) -> None:
        """!poll close without arguments returns usage."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_poll_view_missing_args(self, _dal: _FakeDal) -> None:
        """!poll view without arguments returns usage."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_unknown_subcommand_returns_error(self, _dal: _FakeDal) -> None:
        """Unknown subcommand returns error."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll unknown"))
        assert result is not None
        assert "unknown" in result.payload["text"].lower()

    async def test_missing_text_raises_value_error(self, _dal: _FakeDal) -> None:
        """Event without text raises ValueError."""
        event = PlatformEvent(
            platform="discord",
            event_type="message",
            actor="penguin",
            payload={"channel_id": "chan-1"},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            with pytest.raises(ValueError, match="text"):
                await transform(event)

    async def test_non_string_text_raises_value_error(self, _dal: _FakeDal) -> None:
        """Event with non-string text raises ValueError."""
        event = PlatformEvent(
            platform="discord",
            event_type="message",
            actor="penguin",
            payload={"text": 123, "channel_id": "chan-1"},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            with pytest.raises(ValueError, match="text"):
                await transform(event)

    async def test_whitespace_only_text_returns_none(self, _dal: _FakeDal) -> None:
        """Text with only whitespace returns None."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("   "))
        assert result is None

    async def test_preserves_channel_id_in_reply(self, _dal: _FakeDal) -> None:
        """Reply should preserve channel_id from original event."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll list"))
        if result:
            assert result.payload.get("channel_id") == "chan-1"


class TestParseQuotedArgs:
    """Tests for the quoted argument parser."""

    def test_parse_simple_quoted_args(self) -> None:
        """Parse simple quoted arguments."""
        args = '"title" "opt1" "opt2"'
        result = _parse_quoted_args(args)
        assert result == ["title", "opt1", "opt2"]

    def test_parse_args_with_spaces(self) -> None:
        """Parse arguments with internal spaces."""
        args = '"My Title" "First Option" "Second Option"'
        result = _parse_quoted_args(args)
        assert result == ["My Title", "First Option", "Second Option"]

    def test_parse_args_empty_string(self) -> None:
        """Parse empty string returns empty list."""
        result = _parse_quoted_args("")
        assert result == []

    def test_parse_args_no_quotes(self) -> None:
        """Parse arguments without quotes."""
        result = _parse_quoted_args("arg1 arg2 arg3")
        assert result == ["arg1", "arg2", "arg3"]

    def test_parse_args_mixed_quoted_unquoted(self) -> None:
        """Parse mix of quoted and unquoted."""
        result = _parse_quoted_args('arg1 "arg 2" arg3')
        assert result == ["arg1", "arg 2", "arg3"]

    def test_parse_args_escaped_quotes(self) -> None:
        """Parse escaped quotes within arguments."""
        result = _parse_quoted_args(r'"arg with \" quote"')
        assert result == ['arg with " quote']

    def test_parse_args_trailing_whitespace(self) -> None:
        """Parse with trailing whitespace."""
        result = _parse_quoted_args('"arg1" "arg2"  ')
        assert result == ["arg1", "arg2"]

    def test_parse_args_leading_whitespace(self) -> None:
        """Parse with leading whitespace."""
        result = _parse_quoted_args('  "arg1" "arg2"')
        assert result == ["arg1", "arg2"]


class TestCommunityContext:
    """Tests for community-scoped operations (IDOR fix regression tests)."""

    async def test_poll_create_requires_community_context(self, _dal: _FakeDal) -> None:
        """Create rejects when ctx.community is None (tenant-wide rejection)."""
        with bundle_context(tenant="t1", community=None, app_id="waddles.community.polls.default"):
            result = await transform(_event('!poll create "Poll" "A" "B"'))
        assert result is not None
        assert "community context" in result.payload["text"].lower()

    async def test_poll_vote_requires_community_context(self, _dal: _FakeDal) -> None:
        """Vote rejects when ctx.community is None (tenant-wide rejection)."""
        with bundle_context(tenant="t1", community=None, app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 1 1"))
        assert result is not None
        assert "community context" in result.payload["text"].lower()

    async def test_poll_close_requires_community_context(self, _dal: _FakeDal) -> None:
        """Close rejects when ctx.community is None (tenant-wide rejection)."""
        with bundle_context(tenant="t1", community=None, app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close 1"))
        assert result is not None
        assert "community context" in result.payload["text"].lower()

    async def test_poll_view_requires_community_context(self, _dal: _FakeDal) -> None:
        """View rejects when ctx.community is None (tenant-wide rejection)."""
        with bundle_context(tenant="t1", community=None, app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view 1"))
        assert result is not None
        assert "community context" in result.payload["text"].lower()

    async def test_poll_vote_idor_cross_community_not_found(self, _dal: _FakeDal) -> None:
        """Vote on poll from another community returns not found (IDOR fix)."""
        # Create poll in community 1
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Test Poll",
            "is_active": True,
        }
        _dal._options[1] = {
            "id": 1,
            "poll_id": 1,
            "option_text": "Option A",
            "sort_order": 0,
        }
        # Try to vote from community 2
        with bundle_context(tenant="t1", community="2", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 1 1"))
        assert result is not None
        text_lower = result.payload["text"].lower()
        assert "not found" in text_lower or "closed" in text_lower

    async def test_poll_close_idor_cross_community_not_found(self, _dal: _FakeDal) -> None:
        """Close on poll from another community returns not found (IDOR fix)."""
        # Create poll in community 1
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Test Poll",
            "is_active": True,
        }
        # Try to close from community 2
        with bundle_context(tenant="t1", community="2", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close 1"))
        assert result is not None
        assert "not found" in result.payload["text"].lower()

    async def test_poll_view_idor_cross_community_not_found(self, _dal: _FakeDal) -> None:
        """View poll from another community returns not found (IDOR fix)."""
        # Create poll in community 1
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Test Poll",
            "is_active": True,
        }
        # Try to view from community 2
        with bundle_context(tenant="t1", community="2", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view 1"))
        assert result is not None
        assert "not found" in result.payload["text"].lower()


class TestPollVoteFlow:
    """Full vote handler tests including success paths."""

    async def test_poll_vote_success(self, _dal: _FakeDal) -> None:
        """Successfully vote on a poll."""
        # Create poll with options
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Favorite Color",
            "is_active": True,
        }
        _dal._options[1] = {
            "id": 1,
            "poll_id": 1,
            "option_text": "Red",
            "sort_order": 0,
        }
        _dal._options[2] = {
            "id": 2,
            "poll_id": 1,
            "option_text": "Blue",
            "sort_order": 1,
        }

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 1 2"))
        assert result is not None
        assert "vote recorded" in result.payload["text"].lower()
        assert "option 2" in result.payload["text"].lower()
        assert len(_dal._votes) == 1
        assert _dal._votes[0]["user_id"] == "penguin"

    async def test_poll_vote_option_out_of_range_high(self, _dal: _FakeDal) -> None:
        """Vote on option that exceeds total options."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Test",
            "is_active": True,
        }
        _dal._options[1] = {"id": 1, "poll_id": 1, "option_text": "A", "sort_order": 0}

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 1 5"))
        assert result is not None
        assert "invalid option" in result.payload["text"].lower()

    async def test_poll_vote_option_zero(self, _dal: _FakeDal) -> None:
        """Vote on option 0 (invalid)."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Test",
            "is_active": True,
        }
        _dal._options[1] = {"id": 1, "poll_id": 1, "option_text": "A", "sort_order": 0}

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 1 0"))
        assert result is not None
        assert "invalid option" in result.payload["text"].lower()

    async def test_poll_vote_non_numeric_option(self, _dal: _FakeDal) -> None:
        """Vote with non-numeric option number."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 1 abc"))
        assert result is not None
        assert "numeric" in result.payload["text"].lower()

    async def test_poll_vote_nonexistent_poll(self, _dal: _FakeDal) -> None:
        """Vote on poll that doesn't exist."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll vote 999 1"))
        assert result is not None
        text_lower = result.payload["text"].lower()
        assert "not found" in text_lower or "closed" in text_lower


class TestPollCloseFlow:
    """Full close handler tests including success paths."""

    async def test_poll_close_success(self, _dal: _FakeDal) -> None:
        """Successfully close a poll and display results."""
        # Create poll with options and votes
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Best Language",
            "is_active": True,
        }
        _dal._options[1] = {
            "id": 1,
            "poll_id": 1,
            "option_text": "Python",
            "sort_order": 0,
        }
        _dal._options[2] = {
            "id": 2,
            "poll_id": 1,
            "option_text": "Go",
            "sort_order": 1,
        }
        _dal._votes.append({"poll_id": 1, "option_id": 1, "user_id": "alice"})
        _dal._votes.append({"poll_id": 1, "option_id": 1, "user_id": "bob"})
        _dal._votes.append({"poll_id": 1, "option_id": 2, "user_id": "charlie"})

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close 1"))
        assert result is not None
        assert "closed" in result.payload["text"].lower()
        assert "Best Language" in result.payload["text"]
        assert "Python: 2" in result.payload["text"]
        assert "Go: 1" in result.payload["text"]
        # Verify poll was marked inactive
        assert _dal._polls[1]["is_active"] is False

    async def test_poll_close_no_votes(self, _dal: _FakeDal) -> None:
        """Close a poll with no votes."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Empty Poll",
            "is_active": True,
        }
        _dal._options[1] = {
            "id": 1,
            "poll_id": 1,
            "option_text": "Option",
            "sort_order": 0,
        }

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close 1"))
        assert result is not None
        assert "closed" in result.payload["text"].lower()
        assert "option: 0" in result.payload["text"].lower()

    async def test_poll_close_invalid_poll_id(self, _dal: _FakeDal) -> None:
        """Close with non-numeric poll ID."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close abc"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_poll_close_nonexistent_poll(self, _dal: _FakeDal) -> None:
        """Close poll that doesn't exist."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll close 999"))
        assert result is not None
        assert "not found" in result.payload["text"].lower()


class TestPollViewFlow:
    """Full view handler tests including success paths."""

    async def test_poll_view_active(self, _dal: _FakeDal) -> None:
        """View an active poll with vote counts."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Favorite Framework",
            "is_active": True,
        }
        _dal._options[1] = {
            "id": 1,
            "poll_id": 1,
            "option_text": "Quart",
            "sort_order": 0,
        }
        _dal._options[2] = {
            "id": 2,
            "poll_id": 1,
            "option_text": "FastAPI",
            "sort_order": 1,
        }
        _dal._votes.append({"poll_id": 1, "option_id": 1, "user_id": "alice"})

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view 1"))
        assert result is not None
        assert "poll 1" in result.payload["text"].lower()
        assert "Favorite Framework" in result.payload["text"]
        assert "[active]" in result.payload["text"].lower()
        assert "Quart" in result.payload["text"]
        assert "1. Quart (1 vote)" in result.payload["text"]
        assert "2. FastAPI (0 votes)" in result.payload["text"]
        assert "vote with" in result.payload["text"].lower()

    async def test_poll_view_closed(self, _dal: _FakeDal) -> None:
        """View a closed poll (no vote prompt)."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Closed Poll",
            "is_active": False,
        }
        _dal._options[1] = {
            "id": 1,
            "poll_id": 1,
            "option_text": "Option",
            "sort_order": 0,
        }

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view 1"))
        assert result is not None
        assert "[closed]" in result.payload["text"].lower()
        assert "vote with" not in result.payload["text"].lower()

    async def test_poll_view_no_options(self, _dal: _FakeDal) -> None:
        """View a poll with no options (edge case)."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Empty",
            "is_active": True,
        }

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view 1"))
        assert result is not None
        assert "Empty" in result.payload["text"]

    async def test_poll_view_invalid_poll_id(self, _dal: _FakeDal) -> None:
        """View with non-numeric poll ID."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view abc"))
        assert result is not None
        assert "usage" in result.payload["text"].lower()

    async def test_poll_view_nonexistent_poll(self, _dal: _FakeDal) -> None:
        """View poll that doesn't exist."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll view 999"))
        assert result is not None
        assert "not found" in result.payload["text"].lower()


class TestPollListFlow:
    """Full list handler tests including edge cases."""

    async def test_poll_list_empty(self, _dal: _FakeDal) -> None:
        """List when no active polls exist."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll list"))
        assert result is not None
        assert "no active polls" in result.payload["text"].lower()

    async def test_poll_list_multiple(self, _dal: _FakeDal) -> None:
        """List multiple active polls."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Poll 1",
            "is_active": True,
        }
        _dal._polls[2] = {
            "id": 2,
            "community_id": 1,
            "created_by": "bob",
            "title": "Poll 2",
            "is_active": True,
        }

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll list"))
        assert result is not None
        assert "Poll 1" in result.payload["text"]
        assert "Poll 2" in result.payload["text"]
        assert "active polls" in result.payload["text"].lower()

    async def test_poll_list_filters_inactive(self, _dal: _FakeDal) -> None:
        """List only shows active polls, not closed ones."""
        _dal._polls[1] = {
            "id": 1,
            "community_id": 1,
            "created_by": "alice",
            "title": "Active",
            "is_active": True,
        }
        _dal._polls[2] = {
            "id": 2,
            "community_id": 1,
            "created_by": "bob",
            "title": "Closed",
            "is_active": False,
        }

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event("!poll list"))
        assert result is not None
        assert "Active" in result.payload["text"]
        assert "Closed" not in result.payload["text"]


class TestPollCreateFlow:
    """Full create handler tests including edge cases."""

    async def test_poll_create_with_many_options(self, _dal: _FakeDal) -> None:
        """Create a poll with many options."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(
                _event('!poll create "Languages" "Python" "Go" "Rust" "JS" "Java"')
            )
        assert result is not None
        assert "Poll created" in result.payload["text"]
        assert "Languages" in result.payload["text"]
        assert "Python" in result.payload["text"]
        assert "Java" in result.payload["text"]
        assert len(_dal._options) == 5

    async def test_poll_create_exact_two_options(self, _dal: _FakeDal) -> None:
        """Create poll with exactly 2 options (minimum)."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event('!poll create "Two" "Opt1" "Opt2"'))
        assert result is not None
        assert "Poll created" in result.payload["text"]
        assert len(_dal._options) == 2

    async def test_poll_create_non_numeric_actor(self, _dal: _FakeDal) -> None:
        """Create preserves non-numeric actor as creator."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event('!poll create "Title" "A" "B"', actor="user123"))
        assert result is not None
        assert "Poll created" in result.payload["text"]
        assert _dal._polls[1]["created_by"] == "user123"

    async def test_poll_create_with_special_chars(self, _dal: _FakeDal) -> None:
        """Create poll with special characters in title and options."""
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(
                _event('!poll create "Best #hashtag? (2026)" "Yes!!!" "No..."')
            )
        assert result is not None
        assert "Poll created" in result.payload["text"]
        assert "Best #hashtag? (2026)" in result.payload["text"]
        assert "Yes!!!" in result.payload["text"]

    async def test_poll_create_exception_handling(self, _dal: _FakeDal) -> None:
        """Create handler catches and reports exceptions."""

        class _BadDal(_FakeDal):
            async def execute(self, sql: str, params: Any) -> list[dict[str, Any]]:
                if "insert into community_polls" in sql.lower() and "returning" in sql.lower():
                    raise RuntimeError("Database error")
                return await super().execute(sql, params)

        set_bundle_dal(_BadDal())

        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            result = await transform(_event('!poll create "Title" "A" "B"'))
        assert result is not None
        assert "error" in result.payload["text"].lower()
        reset_bundle_dal_for_tests()
        set_bundle_dal(_dal)


class TestNoReplyBranches:
    """Tests for None return paths."""

    async def test_non_string_text_in_payload(self, _dal: _FakeDal) -> None:
        """Text that's not a string at all gets caught."""
        event = PlatformEvent(
            platform="discord",
            event_type="message",
            actor="penguin",
            payload={"text": 42, "channel_id": "chan-1"},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            with pytest.raises(ValueError):
                await transform(event)

    async def test_text_field_missing(self, _dal: _FakeDal) -> None:
        """Missing text field raises ValueError."""
        event = PlatformEvent(
            platform="discord",
            event_type="message",
            actor="penguin",
            payload={"channel_id": "chan-1"},
            occurred_at="2026-01-01T00:00:00+00:00",
        )
        with bundle_context(tenant="t1", community="1", app_id="waddles.community.polls.default"):
            with pytest.raises(ValueError):
                await transform(event)
