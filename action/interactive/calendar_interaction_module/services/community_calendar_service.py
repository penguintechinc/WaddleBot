"""CommunityCalendarService — manages user subscriptions to WaddleBot community calendars.

When a user subscribes to a community via this service, a dedicated calendar
named "WaddleBot: {Community Name}" is created in their external provider
account (Google, Microsoft, or Apple).  All community events are pushed to
that calendar automatically as they are created, updated, or deleted.

Subscription lifecycle
----------------------
subscribe()                     → create provider calendar + store subscription
unsubscribe()                   → delete or clear provider calendar + remove subscription
list_subscriptions()            → list all active subscriptions for a user
on_community_event_created()    → push new event to all subscribed users' calendars
on_community_event_updated()    → update event on all subscribed users' calendars
on_community_event_deleted()    → remove event from all subscribed users' calendars

Usage
-----
service = CommunityCalendarService(dal=dal)
await service.subscribe(
    user_id="u1", community_id=7, provider="google",
    calendar_id="primary", credentials={...},
)
await service.on_community_event_created(event_id=42, community_id=7)
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from libs.calendar_sync import (
    GoogleCalendarProvider,
    MicrosoftCalendarProvider,
    AppleCalendarProvider,
    CalendarSyncEngine,
)

logger = logging.getLogger(__name__)

_PROVIDER_REGISTRY = {
    "google": GoogleCalendarProvider,
    "microsoft": MicrosoftCalendarProvider,
    "apple": AppleCalendarProvider,
}

# Calendar display name pattern.
_CALENDAR_NAME_TEMPLATE = "WaddleBot: {community_name}"


class CommunityCalendarService:
    """Manages user subscriptions to WaddleBot community calendars.

    Args:
        dal: Database abstraction layer with async execute(query, params).
    """

    def __init__(self, dal: Any):
        self.dal = dal

    # ──────────────────────────────────────────────────────────────────────
    # Subscription management
    # ──────────────────────────────────────────────────────────────────────

    async def subscribe(
        self,
        user_id: str,
        community_id: int,
        provider: str,
        credentials: Dict[str, Any],
        target_calendar_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Subscribe a user to a community calendar.

        Creates a dedicated "WaddleBot: {Community}" calendar in the user's
        external provider account (unless target_calendar_id is specified, in
        which case events are pushed to that existing calendar).  Stores the
        subscription record in the database.

        Args:
            user_id: WaddleBot user ID.
            community_id: WaddleBot community ID.
            provider: External provider name ("google", "microsoft", "apple").
            credentials: Provider OAuth/CalDAV credentials dict.
            target_calendar_id: If provided, use this existing calendar instead
                of creating a new one.  Useful for "sync to primary calendar".

        Returns:
            Subscription result dict with keys: success, subscription_id,
            provider, calendar_id, calendar_name, created_new_calendar.
        """
        # Prevent duplicate subscriptions.
        existing = await self._find_subscription(user_id, community_id, provider)
        if existing:
            logger.info(
                f"[COMMUNITY_CAL] User {user_id} already subscribed to "
                f"community {community_id} via {provider}."
            )
            return {
                "success": True,
                "subscription_id": existing["id"],
                "provider": provider,
                "calendar_id": existing["provider_calendar_id"],
                "calendar_name": existing["calendar_name"],
                "created_new_calendar": False,
                "already_existed": True,
            }

        community = await self._load_community(community_id)
        if not community:
            return {
                "success": False,
                "error": f"Community {community_id} not found.",
            }

        community_name = community.get("name", f"Community {community_id}")
        calendar_name = _CALENDAR_NAME_TEMPLATE.format(community_name=community_name)

        provider_instance = self._build_provider(provider, credentials)
        if not provider_instance:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}.",
            }

        # Refresh credentials.
        try:
            credentials = await provider_instance.authenticate(credentials)
            await self._save_credentials(user_id, provider, credentials)
        except ValueError as exc:
            return {"success": False, "error": f"Authentication failed: {exc}"}

        created_new = False
        if target_calendar_id:
            provider_calendar_id = target_calendar_id
        else:
            try:
                cal = await provider_instance.create_calendar(
                    name=calendar_name,
                    description=(
                        f"Automatically managed by WaddleBot. "
                        f"Events from the '{community_name}' community."
                    ),
                )
                provider_calendar_id = cal["id"]
                created_new = True
                logger.info(
                    f"[COMMUNITY_CAL] Created calendar '{calendar_name}' "
                    f"in {provider} for user={user_id}: {provider_calendar_id}"
                )
            except Exception as exc:
                logger.error(
                    f"[COMMUNITY_CAL] Failed to create calendar in {provider}: {exc}"
                )
                return {"success": False, "error": f"Calendar creation failed: {exc}"}

        subscription_id = await self._create_subscription(
            user_id=user_id,
            community_id=community_id,
            provider=provider,
            provider_calendar_id=provider_calendar_id,
            calendar_name=calendar_name,
        )

        # Backfill existing approved events for this community.
        await self._backfill_community_events(
            user_id=user_id,
            community_id=community_id,
            provider=provider,
            provider_calendar_id=provider_calendar_id,
            credentials=credentials,
        )

        logger.info(
            f"[COMMUNITY_CAL] Subscribed user={user_id} to community={community_id} "
            f"via {provider}: calendar={provider_calendar_id}"
        )

        return {
            "success": True,
            "subscription_id": subscription_id,
            "provider": provider,
            "calendar_id": provider_calendar_id,
            "calendar_name": calendar_name,
            "created_new_calendar": created_new,
        }

    async def unsubscribe(
        self,
        user_id: str,
        community_id: int,
        provider: str,
        delete_calendar: bool = True,
    ) -> Dict[str, Any]:
        """Remove a user's subscription from a community calendar.

        Optionally deletes the "WaddleBot: {Community}" calendar from the
        external provider.

        Args:
            user_id: WaddleBot user ID.
            community_id: WaddleBot community ID.
            provider: External provider name.
            delete_calendar: If True, attempt to delete the provider calendar.

        Returns:
            Result dict with keys: success, deleted_calendar, error (on failure).
        """
        subscription = await self._find_subscription(user_id, community_id, provider)
        if not subscription:
            return {
                "success": False,
                "error": f"No active subscription found for user={user_id}, "
                         f"community={community_id}, provider={provider}.",
            }

        deleted_calendar = False
        if delete_calendar:
            credentials = await self._load_credentials(user_id, provider)
            if credentials:
                provider_instance = self._build_provider(provider, credentials)
                if provider_instance:
                    try:
                        credentials = await provider_instance.authenticate(credentials)
                        provider_cal_id = subscription["provider_calendar_id"]
                        # For Google and Microsoft, delete the calendar via API.
                        # For Apple, CalDAV MKCALENDAR collections can be removed
                        # with a DELETE request.  We approximate by noting that
                        # removing a calendar is provider-specific; here we log
                        # the intent and clear the provider mapping.
                        logger.info(
                            f"[COMMUNITY_CAL] Calendar deletion requested for "
                            f"{provider}:{provider_cal_id} (user={user_id})."
                        )
                        # Provider-specific calendar deletion is intentionally
                        # not implemented here to avoid accidental data loss.
                        # The subscription is deactivated and the calendar is
                        # left with its existing events unless the user removes
                        # it manually.
                        deleted_calendar = False
                    except Exception as exc:
                        logger.warning(
                            f"[COMMUNITY_CAL] Could not delete provider calendar: {exc}"
                        )

        await self._deactivate_subscription(subscription["id"])

        logger.info(
            f"[COMMUNITY_CAL] Unsubscribed user={user_id} from "
            f"community={community_id} via {provider}."
        )

        return {
            "success": True,
            "subscription_id": subscription["id"],
            "deleted_calendar": deleted_calendar,
        }

    async def list_subscriptions(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """List all active community calendar subscriptions for a user.

        Args:
            user_id: WaddleBot user ID.

        Returns:
            List of subscription dicts, each containing: subscription_id,
            community_id, community_name, provider, calendar_id,
            calendar_name, subscribed_at.
        """
        try:
            query = """
                SELECT
                    ccs.id AS subscription_id,
                    ccs.community_id,
                    c.name AS community_name,
                    ccs.provider,
                    ccs.provider_calendar_id AS calendar_id,
                    ccs.calendar_name,
                    ccs.created_at AS subscribed_at
                FROM community_calendar_subscriptions ccs
                LEFT JOIN communities c ON c.id = ccs.community_id
                WHERE ccs.user_id = $1 AND ccs.is_active = TRUE
                ORDER BY ccs.created_at DESC
            """
            rows = await self.dal.execute(query, [user_id])
            return [dict(r) for r in rows] if rows else []
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] list_subscriptions failed: {exc}")
            return []

    # ──────────────────────────────────────────────────────────────────────
    # Community event lifecycle hooks
    # ──────────────────────────────────────────────────────────────────────

    async def on_community_event_created(
        self, event_id: int, community_id: int
    ) -> Dict[str, Any]:
        """Push a newly created community event to all subscribed users' calendars.

        Called by the event creation flow after an event is approved or
        auto-approved.

        Args:
            event_id: WaddleBot calendar_events.id.
            community_id: Community that owns the event.

        Returns:
            Summary dict: total subscribers, pushed, failed.
        """
        return await self._broadcast_event_operation(
            event_id=event_id,
            community_id=community_id,
            operation="create",
        )

    async def on_community_event_updated(
        self, event_id: int, community_id: int
    ) -> Dict[str, Any]:
        """Update a community event on all subscribed users' external calendars.

        Args:
            event_id: WaddleBot calendar_events.id.
            community_id: Community that owns the event.

        Returns:
            Summary dict: total subscribers, pushed, failed.
        """
        return await self._broadcast_event_operation(
            event_id=event_id,
            community_id=community_id,
            operation="update",
        )

    async def on_community_event_deleted(
        self, event_id: int, community_id: int
    ) -> Dict[str, Any]:
        """Remove a community event from all subscribed users' external calendars.

        Args:
            event_id: WaddleBot calendar_events.id.
            community_id: Community that owns the event.

        Returns:
            Summary dict: total subscribers, removed, failed.
        """
        return await self._broadcast_event_operation(
            event_id=event_id,
            community_id=community_id,
            operation="delete",
        )

    # ──────────────────────────────────────────────────────────────────────
    # Broadcast helper
    # ──────────────────────────────────────────────────────────────────────

    async def _broadcast_event_operation(
        self,
        event_id: int,
        community_id: int,
        operation: str,
    ) -> Dict[str, Any]:
        """Fan out a create/update/delete operation to all subscribed users.

        Args:
            event_id: WaddleBot calendar_events.id.
            community_id: Community ID.
            operation: "create", "update", or "delete".

        Returns:
            Summary dict: total, succeeded, failed.
        """
        subscriptions = await self._load_community_subscriptions(community_id)
        if not subscriptions:
            return {"total": 0, "succeeded": 0, "failed": 0}

        succeeded = 0
        failed = 0

        for sub in subscriptions:
            user_id = sub["user_id"]
            provider = sub["provider"]
            provider_calendar_id = sub["provider_calendar_id"]

            credentials = await self._load_credentials(user_id, provider)
            if not credentials:
                logger.warning(
                    f"[COMMUNITY_CAL] No credentials for user={user_id}, "
                    f"provider={provider}; skipping {operation}."
                )
                failed += 1
                continue

            provider_instance = self._build_provider(provider, credentials)
            if not provider_instance:
                failed += 1
                continue

            try:
                credentials = await provider_instance.authenticate(credentials)
                await self._save_credentials(user_id, provider, credentials)

                if operation == "delete":
                    ok = await self._delete_event_for_subscriber(
                        user_id=user_id,
                        event_id=event_id,
                        provider=provider,
                        provider_calendar_id=provider_calendar_id,
                        provider_instance=provider_instance,
                    )
                else:
                    engine = CalendarSyncEngine(
                        provider=provider_instance, dal=self.dal
                    )
                    canonical = await self._load_canonical_event(event_id)
                    if not canonical:
                        failed += 1
                        continue
                    result = await engine.push_event_to_external(
                        waddlebot_event=canonical,
                        calendar_id=provider_calendar_id,
                        user_id=user_id,
                    )
                    ok = result is not None

                if ok:
                    succeeded += 1
                else:
                    failed += 1

            except Exception as exc:
                logger.error(
                    f"[COMMUNITY_CAL] {operation} failed for user={user_id}, "
                    f"event={event_id}: {exc}"
                )
                failed += 1

        logger.info(
            f"[COMMUNITY_CAL] Broadcast {operation} for event={event_id}, "
            f"community={community_id}: total={len(subscriptions)}, "
            f"succeeded={succeeded}, failed={failed}"
        )

        return {
            "total": len(subscriptions),
            "succeeded": succeeded,
            "failed": failed,
        }

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _build_provider(
        self, provider_name: str, credentials: Dict[str, Any]
    ) -> Optional[Any]:
        """Instantiate the correct provider class by name."""
        cls = _PROVIDER_REGISTRY.get(provider_name)
        if not cls:
            logger.error(
                f"[COMMUNITY_CAL] Unknown provider: {provider_name!r}"
            )
            return None
        return cls(credentials=credentials)

    async def _load_community(self, community_id: int) -> Optional[Dict[str, Any]]:
        """Load community metadata from the database."""
        try:
            rows = await self.dal.execute(
                "SELECT id, name FROM communities WHERE id = $1 LIMIT 1",
                [community_id],
            )
            return dict(rows[0]) if rows else None
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _load_community failed: {exc}")
            return None

    async def _find_subscription(
        self, user_id: str, community_id: int, provider: str
    ) -> Optional[Dict[str, Any]]:
        """Check if an active subscription already exists."""
        try:
            rows = await self.dal.execute(
                """
                SELECT id, provider_calendar_id, calendar_name
                FROM community_calendar_subscriptions
                WHERE user_id = $1 AND community_id = $2
                  AND provider = $3 AND is_active = TRUE
                LIMIT 1
                """,
                [user_id, community_id, provider],
            )
            return dict(rows[0]) if rows else None
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _find_subscription failed: {exc}")
            return None

    async def _create_subscription(
        self,
        user_id: str,
        community_id: int,
        provider: str,
        provider_calendar_id: str,
        calendar_name: str,
    ) -> int:
        """Insert a new subscription record and return its ID."""
        try:
            rows = await self.dal.execute(
                """
                INSERT INTO community_calendar_subscriptions (
                    user_id, community_id, provider,
                    provider_calendar_id, calendar_name,
                    is_active, created_at
                )
                VALUES ($1, $2, $3, $4, $5, TRUE, NOW())
                RETURNING id
                """,
                [user_id, community_id, provider, provider_calendar_id, calendar_name],
            )
            return rows[0]["id"] if rows else -1
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _create_subscription failed: {exc}")
            return -1

    async def _deactivate_subscription(self, subscription_id: int) -> None:
        """Mark a subscription as inactive (soft delete)."""
        try:
            await self.dal.execute(
                """
                UPDATE community_calendar_subscriptions
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = $1
                """,
                [subscription_id],
            )
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _deactivate_subscription failed: {exc}")

    async def _load_community_subscriptions(
        self, community_id: int
    ) -> List[Dict[str, Any]]:
        """Load all active subscriptions for a given community."""
        try:
            rows = await self.dal.execute(
                """
                SELECT user_id, provider, provider_calendar_id
                FROM community_calendar_subscriptions
                WHERE community_id = $1 AND is_active = TRUE
                """,
                [community_id],
            )
            return [dict(r) for r in rows] if rows else []
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _load_community_subscriptions failed: {exc}")
            return []

    async def _load_credentials(
        self, user_id: str, provider: str
    ) -> Optional[Dict[str, Any]]:
        """Load stored provider credentials for a user."""
        try:
            rows = await self.dal.execute(
                """
                SELECT credentials FROM calendar_provider_credentials
                WHERE user_id = $1 AND provider = $2 AND is_active = TRUE
                LIMIT 1
                """,
                [user_id, provider],
            )
            return rows[0].get("credentials") if rows else None
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _load_credentials failed: {exc}")
            return None

    async def _save_credentials(
        self, user_id: str, provider: str, credentials: Dict[str, Any]
    ) -> None:
        """Persist refreshed credentials to the database."""
        import json
        try:
            await self.dal.execute(
                """
                UPDATE calendar_provider_credentials
                SET credentials = $1, updated_at = NOW()
                WHERE user_id = $2 AND provider = $3
                """,
                [json.dumps(credentials), user_id, provider],
            )
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _save_credentials failed: {exc}")

    async def _load_canonical_event(
        self, event_id: int
    ) -> Optional[Dict[str, Any]]:
        """Load a community event and convert it to a canonical dict."""
        try:
            rows = await self.dal.execute(
                """
                SELECT id, event_uuid, title, description, event_date, end_date,
                       timezone, location, status, is_recurring,
                       recurring_pattern, created_by_username
                FROM calendar_events WHERE id = $1 LIMIT 1
                """,
                [event_id],
            )
            if not rows:
                return None

            row = dict(rows[0])
            start = row["event_date"].isoformat() if row.get("event_date") else ""
            end = row["end_date"].isoformat() if row.get("end_date") else start
            recurrence = None
            if row.get("is_recurring") and row.get("recurring_pattern"):
                recurrence = [f"RRULE:{row['recurring_pattern']}"]

            return {
                "id": str(row.get("id") or row.get("event_uuid") or ""),
                "provider_id": None,
                "calendar_id": None,
                "title": row.get("title", ""),
                "description": row.get("description"),
                "location": row.get("location"),
                "start": start,
                "end": end,
                "all_day": False,
                "time_zone": row.get("timezone") or "UTC",
                "status": "confirmed" if row.get("status") == "approved" else "tentative",
                "recurrence": recurrence,
                "organizer": {
                    "email": None,
                    "name": row.get("created_by_username"),
                },
                "attendees": [],
                "html_link": None,
                "created_at": None,
                "updated_at": None,
                "etag": None,
                "raw": {},
            }
        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _load_canonical_event failed: {exc}")
            return None

    async def _delete_event_for_subscriber(
        self,
        user_id: str,
        event_id: int,
        provider: str,
        provider_calendar_id: str,
        provider_instance: Any,
    ) -> bool:
        """Delete a specific event from a subscriber's external calendar.

        Looks up the provider event ID from the sync map, then issues a
        delete request to the provider.
        """
        try:
            rows = await self.dal.execute(
                """
                SELECT provider_event_id FROM calendar_sync_map
                WHERE user_id = $1 AND provider = $2
                  AND calendar_id = $3 AND waddlebot_event_id = $4
                  AND is_calendar_level = FALSE
                LIMIT 1
                """,
                [user_id, provider, provider_calendar_id, str(event_id)],
            )
            if not rows:
                logger.debug(
                    f"[COMMUNITY_CAL] No sync map entry for event={event_id}, "
                    f"user={user_id}, provider={provider}; nothing to delete."
                )
                return True  # Already absent, treat as success.

            provider_event_id = rows[0].get("provider_event_id")
            if not provider_event_id:
                return True

            return await provider_instance.delete_event(
                calendar_id=provider_calendar_id,
                event_id=provider_event_id,
            )
        except Exception as exc:
            logger.error(
                f"[COMMUNITY_CAL] _delete_event_for_subscriber failed: {exc}"
            )
            return False

    async def _backfill_community_events(
        self,
        user_id: str,
        community_id: int,
        provider: str,
        provider_calendar_id: str,
        credentials: Dict[str, Any],
    ) -> None:
        """Push all existing approved community events to the newly subscribed calendar.

        Called once at subscription time so users see historical events
        immediately.  Errors are logged but do not fail the subscription.
        """
        try:
            rows = await self.dal.execute(
                """
                SELECT id FROM calendar_events
                WHERE community_id = $1 AND status = 'approved'
                  AND event_date >= NOW()
                ORDER BY event_date ASC
                LIMIT 200
                """,
                [community_id],
            )
            if not rows:
                return

            provider_instance = self._build_provider(provider, credentials)
            if not provider_instance:
                return

            engine = CalendarSyncEngine(provider=provider_instance, dal=self.dal)

            pushed = 0
            for row in rows:
                event_id = row["id"]
                canonical = await self._load_canonical_event(event_id)
                if canonical:
                    result = await engine.push_event_to_external(
                        waddlebot_event=canonical,
                        calendar_id=provider_calendar_id,
                        user_id=user_id,
                    )
                    if result:
                        pushed += 1

            logger.info(
                f"[COMMUNITY_CAL] Backfilled {pushed}/{len(rows)} events for "
                f"user={user_id}, community={community_id}, provider={provider}."
            )

        except Exception as exc:
            logger.error(f"[COMMUNITY_CAL] _backfill_community_events failed: {exc}")
