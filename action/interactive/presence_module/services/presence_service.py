"""Presence Service — application service layer for the presence module.

Coordinates between the HTTP API layer and the presence library (state store
and sync engine).  Also manages per-user settings stored in Redis.
"""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SETTINGS_KEY_PREFIX = "presence:settings"
_DEFAULT_SETTINGS: Dict[str, Any] = {
    "sync_enabled": True,
    "enabled_platforms": ["slack", "teams", "mattermost"],
    "sync_direction": "bidirectional",
}
_VALID_SYNC_DIRECTIONS = frozenset({"bidirectional", "inbound_only", "outbound_only"})


class PresenceService:
    """Service layer bridging the API and presence library components.

    Args:
        state_store: A PresenceStateStore instance.
        sync_engine: A PresenceSyncEngine instance.
        redis_client: Async Redis client for settings storage.
    """

    def __init__(self, state_store, sync_engine, redis_client):
        self._store = state_store
        self._engine = sync_engine
        self._redis = redis_client

    # ──────────────────────────────────────────────────────────────────────
    # Presence operations
    # ──────────────────────────────────────────────────────────────────────

    async def process_presence_update(
        self,
        user_id: str,
        source_platform: str,
        canonical_status: str,
        platform_status: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Validate, persist, and fan-out a presence update.

        Checks user settings before forwarding to the sync engine.  If the
        user has disabled sync or the source platform is not in their enabled
        list, the update is stored but not fanned out.

        Args:
            user_id: The WaddleBot internal user identifier.
            source_platform: Platform that reported the status change.
            canonical_status: One of CANONICAL_STATUSES values.
            platform_status: Raw platform-native status string.
            metadata: Optional supplementary data.

        Returns:
            Dict with ``"stored"``, ``"fanned_out_to"``, and ``"errors"`` keys.
        """
        settings = await self.get_user_settings(user_id)
        sync_enabled = settings.get("sync_enabled", True)
        enabled_platforms = settings.get(
            "enabled_platforms", list(_DEFAULT_SETTINGS["enabled_platforms"])
        )
        sync_direction = settings.get("sync_direction", "bidirectional")

        # If sync is disabled entirely, store but skip fan-out
        if not sync_enabled or source_platform not in enabled_platforms:
            from presence import PresenceStateStore
            from presence.schema import build_presence_event
            record = build_presence_event(
                user_id=user_id,
                source_platform=source_platform,
                canonical_status=canonical_status,
                platform_status=platform_status,
                metadata=metadata,
            )
            await self._store.set_presence(user_id, source_platform, record)
            logger.info(
                "Presence stored without fan-out (sync disabled or platform "
                "not enabled): user=%s platform=%s",
                user_id,
                source_platform,
            )
            return {
                "stored": True,
                "fanned_out_to": [],
                "errors": [],
                "note": "sync disabled or platform not in enabled_platforms",
            }

        # Outbound-only direction: do not accept inbound-only updates for fan-out
        # (store + fan-out normally for bidirectional and outbound_only)
        result = await self._engine.handle_presence_update(
            user_id=user_id,
            source_platform=source_platform,
            canonical_status=canonical_status,
            platform_status=platform_status,
            metadata=metadata,
        )

        # Filter fan-out targets by user's enabled platforms
        result["fanned_out_to"] = [
            p for p in result.get("fanned_out_to", [])
            if p in enabled_platforms
        ]

        return result

    async def get_user_presence(
        self,
        user_id: str,
        platform: Optional[str] = None,
        all_platforms: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve presence data for a user.

        Args:
            user_id: The WaddleBot internal user identifier.
            platform: Optional platform filter.  If provided, return only
                the record for that specific platform.
            all_platforms: If True, return a per-platform breakdown dict.

        Returns:
            Presence record dict, per-platform dict, or None if not found.
        """
        if platform:
            return await self._store.get_presence(user_id, platform=platform)

        if all_platforms:
            records = await self._store.get_all_presence(user_id)
            return records if records else None

        return await self._engine.get_aggregated_presence(user_id)

    # ──────────────────────────────────────────────────────────────────────
    # Settings operations
    # ──────────────────────────────────────────────────────────────────────

    def _settings_key(self, user_id: str) -> str:
        return f"{_SETTINGS_KEY_PREFIX}:{user_id}"

    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Retrieve presence sync settings for a user.

        Returns default settings if no custom settings have been saved.

        Args:
            user_id: The WaddleBot internal user identifier.

        Returns:
            Settings dict with keys matching _DEFAULT_SETTINGS.
        """
        raw = await self._redis.get(self._settings_key(user_id))
        if raw is None:
            return dict(_DEFAULT_SETTINGS)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Corrupt settings for user=%s, returning defaults", user_id
            )
            return dict(_DEFAULT_SETTINGS)

    async def update_user_settings(
        self, user_id: str, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update presence sync settings for a user.

        Only recognised keys are applied; unknown keys are ignored.  Raises
        ValueError for invalid values.

        Args:
            user_id: The WaddleBot internal user identifier.
            updates: Partial settings dict to merge into existing settings.

        Returns:
            The full updated settings dict.

        Raises:
            ValueError: If any provided value fails validation.
        """
        current = await self.get_user_settings(user_id)
        errors: List[str] = []

        if "sync_enabled" in updates:
            val = updates["sync_enabled"]
            if not isinstance(val, bool):
                errors.append("sync_enabled must be a boolean")
            else:
                current["sync_enabled"] = val

        if "enabled_platforms" in updates:
            from presence.schema import PLATFORM_STATUS_MAP
            val = updates["enabled_platforms"]
            if not isinstance(val, list):
                errors.append("enabled_platforms must be a list")
            else:
                unknown = [p for p in val if p not in PLATFORM_STATUS_MAP]
                if unknown:
                    errors.append(
                        f"Unknown platforms: {unknown}. "
                        f"Known: {sorted(PLATFORM_STATUS_MAP.keys())}"
                    )
                else:
                    current["enabled_platforms"] = val

        if "sync_direction" in updates:
            val = updates["sync_direction"]
            if val not in _VALID_SYNC_DIRECTIONS:
                errors.append(
                    f"sync_direction must be one of: {sorted(_VALID_SYNC_DIRECTIONS)}"
                )
            else:
                current["sync_direction"] = val

        if errors:
            raise ValueError("; ".join(errors))

        await self._redis.set(
            self._settings_key(user_id),
            json.dumps(current),
        )
        logger.info("Updated presence settings for user=%s", user_id)
        return current
