"""Presence Collector — aggregation and display formatting helpers.

Provides functions for bulk-aggregating presence across multiple users
(e.g. for the admin hub) and for formatting raw presence data into
human-readable display strings.
"""
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Status display labels for UI rendering
_STATUS_LABELS: Dict[str, str] = {
    "online": "Online",
    "away": "Away",
    "dnd": "Do Not Disturb",
    "offline": "Offline",
}

# Status priority for display sorting (lower = higher priority / more active)
_STATUS_PRIORITY: Dict[str, int] = {
    "online": 0,
    "dnd": 1,
    "away": 2,
    "offline": 3,
}


async def aggregate_for_hub(
    user_ids: List[str],
    state_store,
) -> Dict[str, Any]:
    """Aggregate presence data for a list of users for hub display.

    Fetches the most-recent-wins canonical status for each user and
    groups them by status for efficient rendering in admin dashboards
    or hub views.

    Args:
        user_ids: List of WaddleBot internal user identifiers.
        state_store: A PresenceStateStore instance.

    Returns:
        Dict with keys:
            - ``"by_user"``: Dict[user_id → presence_record]
            - ``"by_status"``: Dict[canonical_status → List[user_id]]
            - ``"summary"``: Dict with counts per canonical status
            - ``"total_users"``: int total users queried
            - ``"active_users"``: int users with any presence record
    """
    by_user: Dict[str, Optional[Dict[str, Any]]] = {}
    by_status: Dict[str, List[str]] = {
        "online": [],
        "away": [],
        "dnd": [],
        "offline": [],
    }

    for user_id in user_ids:
        all_records = await state_store.get_all_presence(user_id)

        if not all_records:
            by_user[user_id] = None
            by_status["offline"].append(user_id)
            continue

        # Most-recent-wins across platforms
        winning = max(
            all_records.values(),
            key=lambda r: (r.get("timestamp", 0), r.get("source_platform", "")),
        )
        by_user[user_id] = winning
        canonical = winning.get("canonical_status", "offline")
        target_bucket = canonical if canonical in by_status else "offline"
        by_status[target_bucket].append(user_id)

    active_users = sum(1 for v in by_user.values() if v is not None)
    summary = {status: len(ids) for status, ids in by_status.items()}

    logger.debug(
        "Aggregated presence for hub: total=%d active=%d",
        len(user_ids),
        active_users,
    )

    return {
        "by_user": by_user,
        "by_status": by_status,
        "summary": summary,
        "total_users": len(user_ids),
        "active_users": active_users,
    }


def format_for_display(
    presence_data: Optional[Dict[str, Any]],
    include_platform_detail: bool = False,
) -> Dict[str, Any]:
    """Format a raw presence record (or aggregated result) for UI display.

    Accepts either:
    - A single presence record dict (output of get_aggregated_presence)
    - A per-platform breakdown dict (output of get_all_presence)
    - None (user has no presence data)

    Args:
        presence_data: Presence record or platform breakdown dict, or None.
        include_platform_detail: If True and presence_data is a per-platform
            breakdown, include per-platform formatted entries in the output.

    Returns:
        Dict with display-ready fields:
            - ``"status"``: Canonical status string
            - ``"label"``: Human-readable status label
            - ``"priority"``: Sort priority (lower = more active)
            - ``"source_platform"``: Platform that last reported the status
            - ``"timestamp"``: Unix epoch of the last update (int)
            - ``"platform_detail"``: Optional list of per-platform records
            - ``"has_presence"``: bool
    """
    if presence_data is None:
        return {
            "status": "offline",
            "label": _STATUS_LABELS["offline"],
            "priority": _STATUS_PRIORITY["offline"],
            "source_platform": None,
            "timestamp": None,
            "platform_detail": [],
            "has_presence": False,
        }

    # Detect whether this is a per-platform breakdown (dict of dicts) or a
    # single record (has "canonical_status" key at top level)
    if "canonical_status" in presence_data:
        # Single aggregated record
        canonical = presence_data.get("canonical_status", "offline")
        result = {
            "status": canonical,
            "label": _STATUS_LABELS.get(canonical, canonical.title()),
            "priority": _STATUS_PRIORITY.get(canonical, 99),
            "source_platform": presence_data.get("source_platform"),
            "timestamp": presence_data.get("timestamp"),
            "has_presence": True,
            "platform_detail": [],
        }

        if include_platform_detail:
            result["platform_detail"] = [_format_single_record(presence_data)]

        return result

    # Per-platform breakdown dict: platform_name → record
    if not presence_data:
        return format_for_display(None)

    # Find winning record for display (most-recent-wins)
    winning = max(
        presence_data.values(),
        key=lambda r: (r.get("timestamp", 0), r.get("source_platform", "")),
    )
    canonical = winning.get("canonical_status", "offline")

    result = {
        "status": canonical,
        "label": _STATUS_LABELS.get(canonical, canonical.title()),
        "priority": _STATUS_PRIORITY.get(canonical, 99),
        "source_platform": winning.get("source_platform"),
        "timestamp": winning.get("timestamp"),
        "has_presence": True,
        "platform_detail": [],
    }

    if include_platform_detail:
        result["platform_detail"] = [
            _format_single_record(rec)
            for rec in sorted(
                presence_data.values(),
                key=lambda r: r.get("source_platform", ""),
            )
        ]

    return result


def _format_single_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single presence record for platform_detail output."""
    canonical = record.get("canonical_status", "offline")
    return {
        "platform": record.get("source_platform"),
        "status": canonical,
        "label": _STATUS_LABELS.get(canonical, canonical.title()),
        "platform_status": record.get("platform_status"),
        "timestamp": record.get("timestamp"),
        "metadata": record.get("metadata", {}),
    }
