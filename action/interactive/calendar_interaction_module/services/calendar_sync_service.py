"""CalendarSyncService — orchestrates calendar sync for individual WaddleBot users.

This service bridges the calendar_sync library (provider-agnostic) with the
calendar_interaction_module's database and configuration layer.

It is responsible for:
- Selecting the correct provider based on user credentials.
- Running full and incremental syncs on demand or via scheduled triggers.
- Pushing WaddleBot community events to a user's external calendar.
- Storing sync results in the module database for audit and reporting.

Usage
-----
service = CalendarSyncService(dal=dal)
await service.sync_calendar(user_id="u1", provider="google", calendar_id="primary")
await service.sync_all_calendars(user_id="u1")
await service.push_community_event(event_id=42, user_id="u1", calendar_id="primary")
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from libs.calendar_sync import (
    CalendarSyncEngine,
    GoogleCalendarProvider,
    MicrosoftCalendarProvider,
    AppleCalendarProvider,
)

logger = logging.getLogger(__name__)

# Map provider name → provider class for dynamic instantiation.
_PROVIDER_REGISTRY = {
    "google": GoogleCalendarProvider,
    "microsoft": MicrosoftCalendarProvider,
    "apple": AppleCalendarProvider,
}


class CalendarSyncService:
    """Orchestrates calendar sync for individual WaddleBot users.

    Args:
        dal: Database abstraction layer with async execute(query, params).
    """

    def __init__(self, dal: Any):
        self.dal = dal

    # ──────────────────────────────────────────────────────────────────────
    # Public: per-calendar sync
    # ──────────────────────────────────────────────────────────────────────

    async def sync_calendar(
        self,
        user_id: str,
        provider: str,
        calendar_id: str,
        community_id: Optional[int] = None,
        force_full: bool = False,
    ) -> Dict[str, Any]:
        """Sync a single external calendar for a user.

        Performs an incremental sync by default; set force_full=True to
        discard the stored sync token and perform a full re-sync.

        Args:
            user_id: WaddleBot user ID.
            provider: Provider name ("google", "microsoft", "apple").
            calendar_id: Provider-specific calendar identifier.
            community_id: Optional community ID to associate synced events with.
            force_full: If True, perform a full sync ignoring stored token.

        Returns:
            Sync result dict with keys: provider, calendar_id, changed/pulled,
            errors, sync_token, duration_ms, timestamp.
        """
        start = datetime.now(timezone.utc)

        credentials = await self._load_credentials(user_id, provider)
        if not credentials:
            logger.warning(
                f"[SYNC_SVC] No credentials for user={user_id}, provider={provider}"
            )
            return {
                "success": False,
                "error": f"No credentials found for provider={provider}",
                "provider": provider,
                "calendar_id": calendar_id,
            }

        provider_instance = await self._build_provider(provider, credentials)
        if not provider_instance:
            return {
                "success": False,
                "error": f"Unknown provider: {provider}",
                "provider": provider,
                "calendar_id": calendar_id,
            }

        # Refresh credentials before sync.
        try:
            credentials = await provider_instance.authenticate(credentials)
            await self._save_credentials(user_id, provider, credentials)
        except ValueError as exc:
            logger.error(
                f"[SYNC_SVC] Authentication failed for user={user_id}, "
                f"provider={provider}: {exc}"
            )
            return {
                "success": False,
                "error": f"Authentication failed: {exc}",
                "provider": provider,
                "calendar_id": calendar_id,
            }

        engine = CalendarSyncEngine(provider=provider_instance, dal=self.dal)

        try:
            if force_full:
                result = await engine.full_sync(
                    user_id=user_id,
                    calendar_id=calendar_id,
                    community_id=community_id,
                )
                changed_count = result.get("pulled", 0)
                error_count = result.get("errors", 0)
                sync_token = result.get("sync_token")
            else:
                result = await engine.incremental_sync(
                    user_id=user_id,
                    calendar_id=calendar_id,
                    community_id=community_id,
                )
                changed_count = result.get("changed", 0)
                error_count = result.get("errors", 0)
                sync_token = result.get("sync_token")

        except Exception as exc:
            logger.error(
                f"[SYNC_SVC] Sync failed for user={user_id}, "
                f"provider={provider}, calendar={calendar_id}: {exc}"
            )
            return {
                "success": False,
                "error": str(exc),
                "provider": provider,
                "calendar_id": calendar_id,
            }

        end = datetime.now(timezone.utc)
        duration_ms = int((end - start).total_seconds() * 1000)

        await self._record_sync_history(
            user_id=user_id,
            provider=provider,
            calendar_id=calendar_id,
            community_id=community_id,
            changed=changed_count,
            errors=error_count,
            sync_token=sync_token,
            duration_ms=duration_ms,
            sync_type="full" if force_full else "incremental",
        )

        logger.info(
            f"[SYNC_SVC] Sync complete: user={user_id}, provider={provider}, "
            f"calendar={calendar_id}, changed={changed_count}, "
            f"errors={error_count}, duration={duration_ms}ms"
        )

        return {
            "success": True,
            "provider": provider,
            "calendar_id": calendar_id,
            "changed": changed_count,
            "errors": error_count,
            "sync_token": sync_token,
            "duration_ms": duration_ms,
            "timestamp": end.isoformat(),
        }

    async def sync_all_calendars(
        self,
        user_id: str,
        community_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Sync all connected external calendars for a user.

        Iterates over every provider+calendar registration stored for the user
        and runs sync_calendar on each.  Results are collected and returned.

        Args:
            user_id: WaddleBot user ID.
            community_id: Optional community ID to associate synced events with.

        Returns:
            List of sync result dicts, one per calendar.
        """
        registrations = await self._load_calendar_registrations(user_id)
        if not registrations:
            logger.info(
                f"[SYNC_SVC] No calendar registrations for user={user_id}"
            )
            return []

        results: List[Dict[str, Any]] = []
        for reg in registrations:
            result = await self.sync_calendar(
                user_id=user_id,
                provider=reg["provider"],
                calendar_id=reg["calendar_id"],
                community_id=community_id,
            )
            results.append(result)

        success_count = sum(1 for r in results if r.get("success"))
        logger.info(
            f"[SYNC_SVC] sync_all_calendars: user={user_id}, "
            f"total={len(results)}, success={success_count}"
        )
        return results

    # ──────────────────────────────────────────────────────────────────────
    # Public: push community event to external calendar
    # ──────────────────────────────────────────────────────────────────────

    async def push_community_event(
        self,
        event_id: int,
        user_id: str,
        provider: str,
        calendar_id: str,
    ) -> Dict[str, Any]:
        """Push a WaddleBot community event to a user's external calendar.

        Loads the community event from the database, converts it to a canonical
        event dict, and delegates to the sync engine's push_event_to_external.

        Args:
            event_id: WaddleBot calendar_events.id.
            user_id: WaddleBot user ID (owner of the external calendar).
            provider: Target provider name ("google", "microsoft", "apple").
            calendar_id: Target provider calendar identifier.

        Returns:
            Result dict with keys: success, event_id, provider, calendar_id,
            provider_event_id (on success), error (on failure).
        """
        community_event = await self._load_community_event(event_id)
        if not community_event:
            return {
                "success": False,
                "event_id": event_id,
                "error": f"Community event {event_id} not found.",
            }

        credentials = await self._load_credentials(user_id, provider)
        if not credentials:
            return {
                "success": False,
                "event_id": event_id,
                "error": f"No credentials for provider={provider}.",
            }

        provider_instance = await self._build_provider(provider, credentials)
        if not provider_instance:
            return {
                "success": False,
                "event_id": event_id,
                "error": f"Unknown provider: {provider}.",
            }

        try:
            credentials = await provider_instance.authenticate(credentials)
            await self._save_credentials(user_id, provider, credentials)
        except ValueError as exc:
            return {
                "success": False,
                "event_id": event_id,
                "error": f"Authentication failed: {exc}",
            }

        canonical = self._community_event_to_canonical(community_event)
        engine = CalendarSyncEngine(provider=provider_instance, dal=self.dal)

        result = await engine.push_event_to_external(
            waddlebot_event=canonical,
            calendar_id=calendar_id,
            user_id=user_id,
        )

        if result:
            logger.info(
                f"[SYNC_SVC] Pushed community event {event_id} to "
                f"{provider}:{calendar_id} for user={user_id}"
            )
            return {
                "success": True,
                "event_id": event_id,
                "provider": provider,
                "calendar_id": calendar_id,
                "provider_event_id": result.get("provider_id"),
            }
        else:
            return {
                "success": False,
                "event_id": event_id,
                "error": "push_event_to_external returned no result.",
            }

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    async def _build_provider(
        self, provider_name: str, credentials: Dict[str, Any]
    ) -> Optional[Any]:
        """Instantiate the correct provider class by name."""
        cls = _PROVIDER_REGISTRY.get(provider_name)
        if not cls:
            logger.error(
                f"[SYNC_SVC] Unknown provider: {provider_name!r}. "
                f"Known providers: {list(_PROVIDER_REGISTRY)}"
            )
            return None
        return cls(credentials=credentials)

    async def _load_credentials(
        self, user_id: str, provider: str
    ) -> Optional[Dict[str, Any]]:
        """Load OAuth/CalDAV credentials for a user+provider from the database."""
        try:
            query = """
                SELECT credentials
                FROM calendar_provider_credentials
                WHERE user_id = $1 AND provider = $2 AND is_active = TRUE
                LIMIT 1
            """
            rows = await self.dal.execute(query, [user_id, provider])
            if rows:
                return rows[0].get("credentials") or {}
            return None
        except Exception as exc:
            logger.error(f"[SYNC_SVC] _load_credentials failed: {exc}")
            return None

    async def _save_credentials(
        self, user_id: str, provider: str, credentials: Dict[str, Any]
    ) -> None:
        """Persist refreshed credentials back to the database."""
        import json
        try:
            query = """
                UPDATE calendar_provider_credentials
                SET credentials = $1, updated_at = NOW()
                WHERE user_id = $2 AND provider = $3
            """
            await self.dal.execute(query, [json.dumps(credentials), user_id, provider])
        except Exception as exc:
            logger.error(f"[SYNC_SVC] _save_credentials failed: {exc}")

    async def _load_calendar_registrations(
        self, user_id: str
    ) -> List[Dict[str, Any]]:
        """Load all calendar registrations (provider + calendar_id) for a user."""
        try:
            query = """
                SELECT provider, calendar_id
                FROM calendar_sync_registrations
                WHERE user_id = $1 AND is_active = TRUE
                ORDER BY provider, calendar_id
            """
            rows = await self.dal.execute(query, [user_id])
            return [dict(r) for r in rows] if rows else []
        except Exception as exc:
            logger.error(f"[SYNC_SVC] _load_calendar_registrations failed: {exc}")
            return []

    async def _load_community_event(
        self, event_id: int
    ) -> Optional[Dict[str, Any]]:
        """Load a community event dict from calendar_events by ID."""
        try:
            query = """
                SELECT
                    id, event_uuid, title, description, event_date, end_date,
                    timezone, location, status, is_recurring, recurring_pattern,
                    recurring_end_date, created_by_username
                FROM calendar_events
                WHERE id = $1
                LIMIT 1
            """
            rows = await self.dal.execute(query, [event_id])
            return dict(rows[0]) if rows else None
        except Exception as exc:
            logger.error(f"[SYNC_SVC] _load_community_event failed: {exc}")
            return None

    def _community_event_to_canonical(
        self, db_event: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert a calendar_events DB row to a canonical event dict."""
        event_date = db_event.get("event_date")
        end_date = db_event.get("end_date")
        time_zone = db_event.get("timezone", "UTC") or "UTC"

        start_str = event_date.isoformat() if event_date else ""
        end_str = end_date.isoformat() if end_date else start_str

        recurrence = None
        if db_event.get("is_recurring") and db_event.get("recurring_pattern"):
            recurrence = [f"RRULE:{db_event['recurring_pattern']}"]

        return {
            "id": str(db_event.get("id") or db_event.get("event_uuid") or ""),
            "provider_id": None,
            "calendar_id": None,
            "title": db_event.get("title", ""),
            "description": db_event.get("description"),
            "location": db_event.get("location"),
            "start": start_str,
            "end": end_str,
            "all_day": False,
            "time_zone": time_zone,
            "status": "confirmed" if db_event.get("status") == "approved" else "tentative",
            "recurrence": recurrence,
            "organizer": {
                "email": None,
                "name": db_event.get("created_by_username"),
            },
            "attendees": [],
            "html_link": None,
            "created_at": None,
            "updated_at": None,
            "etag": None,
            "raw": {},
        }

    async def _record_sync_history(
        self,
        user_id: str,
        provider: str,
        calendar_id: str,
        community_id: Optional[int],
        changed: int,
        errors: int,
        sync_token: Optional[str],
        duration_ms: int,
        sync_type: str,
    ) -> None:
        """Persist a sync history record for auditing and monitoring."""
        try:
            query = """
                INSERT INTO calendar_sync_history (
                    user_id, provider, calendar_id, community_id,
                    sync_type, changed_count, error_count,
                    sync_token, duration_ms, synced_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
            """
            await self.dal.execute(query, [
                user_id, provider, calendar_id, community_id,
                sync_type, changed, errors, sync_token, duration_ms,
            ])
        except Exception as exc:
            # History logging must never break the sync itself.
            logger.error(f"[SYNC_SVC] _record_sync_history failed: {exc}")
