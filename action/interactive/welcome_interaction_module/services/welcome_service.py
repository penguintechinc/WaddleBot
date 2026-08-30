"""Welcome Service.

social.welcome: recognize a user's first-ever message in a community and
welcome them -- via AI if the `waddles.social.welcome_ai` flag is on for
the caller's tenant/community, else a configurable template.

Two independent checks compose to make this safe:
- `is_first_time`: a cheap read against `activity_message_events`
  (migration 044) that lets most calls (returning users) short-circuit
  before touching the guard table at all.
- `try_mark_welcomed`: the actual correctness guarantee. It relies on
  `community_welcomed_users`'s UNIQUE(community_id, platform,
  platform_user_id) index (migration 068) plus `INSERT ... ON CONFLICT
  DO NOTHING RETURNING id` -- the database, not `is_first_time`, is what
  makes "welcomed at most once, ever" hold under concurrent duplicate
  first-messages.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Protocol

from flask_core import feature_enabled

from config import Config

logger = logging.getLogger(__name__)


class SqlExecutor(Protocol):
    """The DAL surface this module depends on -- `AsyncDAL.execute` shape."""

    async def execute(
        self, sql: str, params: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Run parameterized SQL, returning rows as dicts (empty if none)."""
        ...


@dataclass(slots=True, frozen=True)
class WelcomeResult:
    """Outcome of a first-message welcome check."""

    welcomed: bool
    message: str | None = None
    source: str | None = None  # "ai" | "template", set only when welcomed


async def is_first_time(
    dal: SqlExecutor, community_id: int, platform: str, platform_user_id: str
) -> bool:
    """Return True if this user has no prior message event in this community.

    Args:
        dal: Database executor (penguin-dal/pydal `AsyncDAL.execute`).
        community_id: Community the message was sent in.
        platform: Source platform (twitch, discord, slack, ...).
        platform_user_id: User's platform-native ID.

    Returns:
        True if `activity_message_events` has zero rows for this user in
        this community; False otherwise.

    """
    rows = await dal.execute(
        "SELECT id FROM activity_message_events "
        "WHERE community_id = $1 AND platform = $2 AND platform_user_id = $3 "
        "LIMIT 1",
        [community_id, platform, platform_user_id],
    )
    return len(rows) == 0


async def try_mark_welcomed(
    dal: SqlExecutor, community_id: int, platform: str, platform_user_id: str
) -> bool:
    """Atomically claim the one-time welcome for this user in this community.

    Args:
        dal: Database executor (penguin-dal/pydal `AsyncDAL.execute`).
        community_id: Community the user is being welcomed in.
        platform: Source platform.
        platform_user_id: User's platform-native ID.

    Returns:
        True only if this call's INSERT actually created the row (i.e. the
        caller won the race and should send the welcome). False means
        someone else already claimed it -- never welcome in that case.

    """
    rows = await dal.execute(
        "INSERT INTO community_welcomed_users "
        "(community_id, platform, platform_user_id) "
        "VALUES ($1, $2, $3) "
        "ON CONFLICT (community_id, platform, platform_user_id) DO NOTHING "
        "RETURNING id",
        [community_id, platform, platform_user_id],
    )
    return len(rows) == 1


async def build_welcome(
    *,
    ai_client: Any,
    platform_username: str,
    platform_user_id: str,
    platform: str,
    community_id: int,
    tenant: str,
) -> tuple[str, str]:
    """Build the welcome text -- AI-personalized if flagged on, else template.

    An AI failure/timeout never leaves the user un-welcomed: any exception
    or empty response degrades straight to the template.

    Args:
        ai_client: Object satisfying `AIResponder.generate_response(...)`.
        platform_username: Display name to greet.
        platform_user_id: User's platform-native ID.
        platform: Source platform.
        community_id: Community the user is being welcomed in.
        tenant: Tenant slug (mandatory JWT claim) for the flag check.

    Returns:
        (text, source) where source is "ai" or "template".

    """
    ai_on = await feature_enabled(
        Config.WELCOME_AI_FLAG_KEY,
        tenant=tenant,
        community=community_id,
        default=False,
    )

    if ai_on:
        text: str | None = None
        try:
            text = await asyncio.wait_for(
                ai_client.generate_response(
                    message_content=(
                        "Write one short, warm, single-sentence welcome "
                        f"message for a new community member named "
                        f"{platform_username}."
                    ),
                    message_type='chatMessage',
                    user_id=platform_user_id,
                    platform=platform,
                    context={
                        'trigger_type': 'first_message_welcome',
                        'username': platform_username,
                    },
                ),
                timeout=Config.AI_WELCOME_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 - AI hiccup must not block welcome
            logger.warning(f"AI welcome generation failed, using template: {exc}")

        if text:
            return text, 'ai'
        logger.info("AI welcome flag on but no usable response; using template")

    return Config.WELCOME_TEMPLATE.format(username=platform_username), 'template'


@dataclass(slots=True)
class WelcomeService:
    """Ties first-seen detection, the welcomed guard, and message build together."""

    dal: SqlExecutor
    ai_client: Any

    async def check_and_welcome(
        self,
        *,
        community_id: int,
        platform: str,
        platform_user_id: str,
        platform_username: str,
        tenant: str,
    ) -> WelcomeResult:
        """Run the full first-message welcome flow for one incoming message.

        Args:
            community_id: Community the message was sent in.
            platform: Source platform.
            platform_user_id: User's platform-native ID.
            platform_username: Display name to greet if welcomed.
            tenant: Tenant slug for the AI feature-flag check.

        Returns:
            WelcomeResult(welcomed=True, message=..., source=...) only when
            this call won the race to welcome a genuinely first-time user;
            WelcomeResult(welcomed=False) otherwise.

        """
        if not await is_first_time(self.dal, community_id, platform, platform_user_id):
            return WelcomeResult(welcomed=False)

        newly_claimed = await try_mark_welcomed(
            self.dal, community_id, platform, platform_user_id
        )
        if not newly_claimed:
            return WelcomeResult(welcomed=False)

        text, source = await build_welcome(
            ai_client=self.ai_client,
            platform_username=platform_username,
            platform_user_id=platform_user_id,
            platform=platform,
            community_id=community_id,
            tenant=tenant,
        )
        return WelcomeResult(welcomed=True, message=text, source=source)
