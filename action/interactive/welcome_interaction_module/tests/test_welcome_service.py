"""Unit tests for welcome_service.py.

Covers is_first_time (prior-event detection against
activity_message_events), try_mark_welcomed (idempotent, race-safe
welcomed guard), and build_welcome / WelcomeService.check_and_welcome
(AI-flag gating with graceful fallback to the template on any AI failure).
"""
import asyncio
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from services.welcome_service import (
    WelcomeService,
    build_welcome,
    is_first_time,
    try_mark_welcomed,
)


class FakeAsyncDAL:
    """In-memory stand-in for `AsyncDAL.execute`.

    Models exactly the two query shapes welcome_service issues: an
    existence SELECT against `activity_message_events`, and an
    `INSERT ... ON CONFLICT DO NOTHING RETURNING id` against
    `community_welcomed_users`.

    The welcomed-guard branch performs its check-and-set with no `await`
    between them (after a single upfront `await asyncio.sleep(0)`), the same
    way a real UNIQUE index + ON CONFLICT DO NOTHING is atomic at the
    database layer -- this is what makes the race-safety test meaningful
    under `asyncio.gather` rather than just asserting sequential behavior.
    """

    def __init__(self) -> None:
        """Start with no prior events and no welcomed users."""
        self._events: set[tuple[int, str, str]] = set()
        self._welcomed: dict[tuple[int, str, str], int] = {}
        self._next_id = 1
        self.insert_attempts = 0

    def seed_event(
        self, community_id: int, platform: str, platform_user_id: str
    ) -> None:
        """Record a prior `activity_message_events` row for this user."""
        self._events.add((community_id, platform, platform_user_id))

    async def execute(
        self, sql: str, params: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Dispatch on the table name referenced in `sql`."""
        params = params or []
        if "activity_message_events" in sql:
            key = (params[0], params[1], params[2])
            return [{"id": 1}] if key in self._events else []

        if "community_welcomed_users" in sql:
            self.insert_attempts += 1
            key = (params[0], params[1], params[2])
            await asyncio.sleep(0)  # simulate latency before the DB's atomic check
            if key in self._welcomed:
                return []
            self._welcomed[key] = self._next_id
            self._next_id += 1
            return [{"id": self._welcomed[key]}]

        raise ValueError(f"FakeAsyncDAL: unrecognized query: {sql}")


class FakeAIResponder:
    """Records calls and returns a canned response, or raises."""

    def __init__(
        self,
        response: str | None = "Hey there!",
        raise_exc: Exception | None = None,
    ):
        """Configure the canned response (or exception) this fake will return."""
        self.response = response
        self.raise_exc = raise_exc
        self.calls: list[dict[str, Any]] = []

    async def generate_response(
        self, message_content, message_type, user_id, platform, context
    ):
        """Record the call and return `self.response`, or raise `self.raise_exc`."""
        self.calls.append({
            "message_content": message_content,
            "message_type": message_type,
            "user_id": user_id,
            "platform": platform,
            "context": context,
        })
        if self.raise_exc:
            raise self.raise_exc
        return self.response


class TestIsFirstTime:
    """is_first_time: existence check against activity_message_events."""

    @pytest.mark.asyncio
    async def test_no_prior_event_is_first(self):
        """No rows for this user in this community -> first-time."""
        dal = FakeAsyncDAL()
        assert await is_first_time(dal, 1, "twitch", "user-1") is True

    @pytest.mark.asyncio
    async def test_with_prior_event_is_not_first(self):
        """A prior row for this user in this community -> not first-time."""
        dal = FakeAsyncDAL()
        dal.seed_event(1, "twitch", "user-1")
        assert await is_first_time(dal, 1, "twitch", "user-1") is False

    @pytest.mark.asyncio
    async def test_prior_event_scoped_to_community_and_platform(self):
        """A prior event only counts for its own (community, platform) pair."""
        dal = FakeAsyncDAL()
        dal.seed_event(1, "twitch", "user-1")
        # Same user, different community -> still first there
        assert await is_first_time(dal, 2, "twitch", "user-1") is True
        # Same user, different platform -> still first there
        assert await is_first_time(dal, 1, "discord", "user-1") is True


class TestWelcomedGuard:
    """try_mark_welcomed: idempotent, race-safe one-time claim."""

    @pytest.mark.asyncio
    async def test_first_call_welcomes(self):
        """The first claim for a user succeeds."""
        dal = FakeAsyncDAL()
        assert await try_mark_welcomed(dal, 1, "twitch", "user-1") is True

    @pytest.mark.asyncio
    async def test_second_call_is_noop(self):
        """A second claim for the same user is a no-op."""
        dal = FakeAsyncDAL()
        first = await try_mark_welcomed(dal, 1, "twitch", "user-1")
        second = await try_mark_welcomed(dal, 1, "twitch", "user-1")
        assert first is True
        assert second is False

    @pytest.mark.asyncio
    async def test_concurrent_duplicate_is_race_safe(self):
        """Two concurrent claims for the same user yield exactly one True.

        The DB unique index, not application logic, is the source of truth.
        """
        dal = FakeAsyncDAL()
        results = await asyncio.gather(
            try_mark_welcomed(dal, 1, "twitch", "user-1"),
            try_mark_welcomed(dal, 1, "twitch", "user-1"),
        )
        assert sorted(results) == [False, True]
        assert dal.insert_attempts == 2
        assert len(dal._welcomed) == 1


class TestBuildWelcome:
    """build_welcome: AI-flag gating with graceful fallback."""

    @pytest.mark.asyncio
    async def test_flag_off_uses_template_and_ai_not_called(self):
        """Flag OFF uses the template and never invokes the AI client."""
        ai_client = FakeAIResponder(response="should not be used")
        with patch(
            "services.welcome_service.feature_enabled",
            new=AsyncMock(return_value=False),
        ):
            text, source = await build_welcome(
                ai_client=ai_client,
                platform_username="jdoe",
                platform_user_id="user-1",
                platform="twitch",
                community_id=1,
                tenant="global",
            )
        assert source == "template"
        assert "jdoe" in text
        assert ai_client.calls == []

    @pytest.mark.asyncio
    async def test_flag_on_calls_ai_and_uses_its_response(self):
        """Flag ON calls the AI client and returns its generated text."""
        ai_client = FakeAIResponder(response="Welcome aboard, jdoe!")
        with patch(
            "services.welcome_service.feature_enabled",
            new=AsyncMock(return_value=True),
        ):
            text, source = await build_welcome(
                ai_client=ai_client,
                platform_username="jdoe",
                platform_user_id="user-1",
                platform="twitch",
                community_id=1,
                tenant="global",
            )
        assert source == "ai"
        assert text == "Welcome aboard, jdoe!"
        assert len(ai_client.calls) == 1

    @pytest.mark.asyncio
    async def test_flag_on_ai_failure_falls_back_to_template(self):
        """Flag ON but the AI call raises -> falls back to the template."""
        ai_client = FakeAIResponder(raise_exc=RuntimeError("provider down"))
        with patch(
            "services.welcome_service.feature_enabled",
            new=AsyncMock(return_value=True),
        ):
            text, source = await build_welcome(
                ai_client=ai_client,
                platform_username="jdoe",
                platform_user_id="user-1",
                platform="twitch",
                community_id=1,
                tenant="global",
            )
        assert source == "template"
        assert "jdoe" in text
        assert len(ai_client.calls) == 1  # AI was attempted, just failed


class TestCheckAndWelcome:
    """WelcomeService.check_and_welcome: the full first-message flow."""

    @pytest.mark.asyncio
    async def test_first_time_user_gets_welcomed_once(self):
        """A first-time user is welcomed once; a repeat call is a no-op."""
        dal = FakeAsyncDAL()
        ai_client = FakeAIResponder()
        service = WelcomeService(dal=dal, ai_client=ai_client)

        with patch(
            "services.welcome_service.feature_enabled",
            new=AsyncMock(return_value=False),
        ):
            first = await service.check_and_welcome(
                community_id=1, platform="twitch", platform_user_id="user-1",
                platform_username="jdoe", tenant="global",
            )
            second = await service.check_and_welcome(
                community_id=1, platform="twitch", platform_user_id="user-1",
                platform_username="jdoe", tenant="global",
            )

        assert first.welcomed is True
        assert first.source == "template"
        assert second.welcomed is False

    @pytest.mark.asyncio
    async def test_returning_user_never_welcomed(self):
        """A user with a prior message event is never welcomed."""
        dal = FakeAsyncDAL()
        dal.seed_event(1, "twitch", "user-1")
        service = WelcomeService(dal=dal, ai_client=FakeAIResponder())

        result = await service.check_and_welcome(
            community_id=1, platform="twitch", platform_user_id="user-1",
            platform_username="jdoe", tenant="global",
        )
        assert result.welcomed is False
        assert dal.insert_attempts == 0  # short-circuited before the guard
