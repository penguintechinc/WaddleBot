"""
Group Availability Service - Multi-member appointment scheduling

Handles group booking page functionality:
- Group booking page creation (community-scoped)
- Member management (add/remove members)
- Aggregate availability calculation across multiple members
- Privacy-preserving slot aggregation (no individual calendar exposure)
- "Best slots" ranking across date ranges
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class GroupAvailabilityService:
    """
    Group availability service for multi-member appointment scheduling.

    Features:
    - Group booking page CRUD operations
    - Member management with required/optional designation
    - Privacy-preserving availability aggregation
    - Slot ranking across date ranges
    - No exposure of individual member calendar details
    """

    def __init__(self, dal):
        """
        Initialize group availability service with database abstraction layer.

        Args:
            dal: Database abstraction layer
        """
        self.dal = dal

    async def create_group_booking_page(
        self,
        community_id: int,
        admin_user_id: int,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create a group booking page for a community.

        Args:
            community_id: Community ID (page owner)
            admin_user_id: Admin user creating the page
            data: Booking page configuration with keys:
                - slug: URL slug (unique)
                - title: Page title
                - description: Page description
                - slot_duration: Duration in minutes (default 30)
                - access_scope: 'public', 'registered', 'community' (default 'public')
                - form_fields: Optional custom form fields (max 8)

        Returns:
            Group booking page dict or None on failure
        """
        try:
            query = """
                INSERT INTO booking_pages (
                    slug, page_type, community_id, title, description,
                    slot_duration, access_scope, form_fields
                )
                VALUES ($1, 'group', $2, $3, $4, $5, $6, $7)
                RETURNING id, slug, title, description, slot_duration,
                          access_scope, form_fields, created_at
            """
            result = await self.dal.execute(query, [
                data.get('slug'),
                community_id,
                data.get('title'),
                data.get('description'),
                data.get('slot_duration', 30),
                data.get('access_scope', 'public'),
                data.get('form_fields', [])
            ])

            if result and len(result) > 0:
                row = result[0]
                logger.info(
                    f"[AUDIT] Group booking page created: id={row['id']}, "
                    f"slug={row['slug']}, community={community_id}, admin={admin_user_id}"
                )
                return {
                    'id': row['id'],
                    'slug': row['slug'],
                    'title': row['title'],
                    'description': row['description'],
                    'slot_duration': row['slot_duration'],
                    'access_scope': row['access_scope'],
                    'form_fields': row['form_fields'],
                    'created_at': row['created_at'].isoformat()
                }
            return None

        except Exception as e:
            logger.error(f"[ERROR] Failed to create group booking page: {e}")
            return None

    async def add_member(
        self,
        page_id: int,
        user_id: int,
        is_required: bool = True
    ) -> bool:
        """
        Add a member to a group booking page.

        Args:
            page_id: Group booking page ID
            user_id: Hub user ID to add
            is_required: Whether member must be available for slot to show

        Returns:
            True on success, False on failure
        """
        try:
            # Verify page is group type
            check_query = """
                SELECT id FROM booking_pages
                WHERE id = $1 AND page_type = 'group' AND is_active = TRUE
            """
            check_result = await self.dal.execute(check_query, [page_id])

            if not check_result or len(check_result) == 0:
                logger.warning(f"Group booking page {page_id} not found")
                return False

            # Add member
            query = """
                INSERT INTO booking_page_members (
                    booking_page_id, hub_user_id, is_required
                )
                VALUES ($1, $2, $3)
                ON CONFLICT (booking_page_id, hub_user_id)
                DO UPDATE SET is_required = EXCLUDED.is_required
                RETURNING id
            """
            result = await self.dal.execute(query, [page_id, user_id, is_required])

            if result and len(result) > 0:
                logger.info(
                    f"[AUDIT] Member added to group page: page={page_id}, "
                    f"user={user_id}, required={is_required}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to add member: {e}")
            return False

    async def remove_member(
        self,
        page_id: int,
        user_id: int
    ) -> bool:
        """
        Remove a member from a group booking page.

        Args:
            page_id: Group booking page ID
            user_id: Hub user ID to remove

        Returns:
            True on success, False on failure
        """
        try:
            query = """
                DELETE FROM booking_page_members
                WHERE booking_page_id = $1 AND hub_user_id = $2
                RETURNING id
            """
            result = await self.dal.execute(query, [page_id, user_id])

            if result and len(result) > 0:
                logger.info(
                    f"[AUDIT] Member removed from group page: page={page_id}, user={user_id}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to remove member: {e}")
            return False

    async def get_group_members(
        self,
        page_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get member list for a group booking page (names only, no calendar data).

        Args:
            page_id: Group booking page ID

        Returns:
            List of member dicts with id, username, is_required
        """
        try:
            query = """
                SELECT m.hub_user_id, m.is_required, u.username
                FROM booking_page_members m
                JOIN hub_users u ON m.hub_user_id = u.id
                WHERE m.booking_page_id = $1
                ORDER BY m.is_required DESC, u.username ASC
            """
            result = await self.dal.execute(query, [page_id])

            members = []
            for row in result:
                members.append({
                    'user_id': row['hub_user_id'],
                    'username': row['username'],
                    'is_required': row['is_required']
                })

            return members

        except Exception as e:
            logger.error(f"[ERROR] Failed to get group members: {e}")
            return []

    async def get_group_availability(
        self,
        page_id: int,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Aggregate availability for all members in a group booking page.

        Privacy-preserving: Returns only aggregate counts, NOT individual calendars.

        Logic:
        1. Get all members and their settings
        2. For each member, compute their available slots (like individual booking)
        3. Find overlapping slots where required members are ALL available
        4. Return slots with availability counts (available/maybe/unavailable)
        5. DO NOT expose individual member calendar details

        Args:
            page_id: Group booking page ID
            date: Date to check (datetime object, time component ignored)

        Returns:
            List of slot dicts with:
                - start: ISO timestamp
                - end: ISO timestamp
                - available_count: Number of members available
                - maybe_count: Number of members tentatively available
                - unavailable_count: Number of members unavailable
                - meets_requirements: Boolean (all required members available)
        """
        try:
            # Step 1: Get booking page config
            page_query = """
                SELECT slot_duration FROM booking_pages
                WHERE id = $1 AND page_type = 'group' AND is_active = TRUE
            """
            page_result = await self.dal.execute(page_query, [page_id])

            if not page_result or len(page_result) == 0:
                logger.warning(f"Group booking page {page_id} not found")
                return []

            slot_duration = page_result[0]['slot_duration']

            # Step 2: Get all members
            members = await self.get_group_members(page_id)

            if not members:
                logger.warning(f"No members for group page {page_id}")
                return []

            # Normalize date to start of day in UTC
            check_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = check_date + timedelta(days=1)
            day_name = check_date.strftime('%A').lower()

            # Step 3: Collect availability for each member
            member_slots = {}
            required_members = []

            for member in members:
                user_id = member['user_id']
                is_required = member['is_required']

                if is_required:
                    required_members.append(user_id)

                # Get member's calendar settings
                settings_query = """
                    SELECT weekly_availability, timezone, min_notice_hours,
                           max_future_days, buffer_minutes
                    FROM user_calendar_settings
                    WHERE hub_user_id = $1
                """
                settings_result = await self.dal.execute(settings_query, [user_id])

                if not settings_result or len(settings_result) == 0:
                    # Member has no settings - treat as unavailable
                    member_slots[user_id] = []
                    continue

                settings = settings_result[0]
                weekly_availability = settings.get('weekly_availability', {})
                min_notice_hours = settings.get('min_notice_hours', 4)
                max_future_days = settings.get('max_future_days', 30)
                buffer_minutes = settings.get('buffer_minutes', 0)

                # Apply min_notice and max_future constraints
                now = datetime.now(timezone.utc)
                earliest_slot = now + timedelta(hours=min_notice_hours)
                latest_slot = now + timedelta(days=max_future_days)

                # Get day availability
                day_availability = weekly_availability.get(day_name, [])

                if not day_availability:
                    member_slots[user_id] = []
                    continue

                # Generate candidate slots for this member
                candidate_slots = []
                for block in day_availability:
                    start_time_str = block.get('start')
                    end_time_str = block.get('end')

                    if not start_time_str or not end_time_str:
                        continue

                    start_hour, start_minute = map(int, start_time_str.split(':'))
                    end_hour, end_minute = map(int, end_time_str.split(':'))

                    block_start = check_date.replace(hour=start_hour, minute=start_minute)
                    block_end = check_date.replace(hour=end_hour, minute=end_minute)

                    current = block_start
                    while current + timedelta(minutes=slot_duration) <= block_end:
                        slot_end = current + timedelta(minutes=slot_duration)

                        if current >= earliest_slot and current <= latest_slot:
                            candidate_slots.append({
                                'start': current,
                                'end': slot_end
                            })

                        current = slot_end + timedelta(minutes=buffer_minutes)

                # Get member's free/busy blocks
                busy_query = """
                    SELECT start_time, end_time
                    FROM calendar_free_busy
                    WHERE hub_user_id = $1
                      AND start_time < $2
                      AND end_time > $3
                      AND status IN ('busy', 'tentative')
                """
                busy_result = await self.dal.execute(busy_query, [
                    user_id, day_end, check_date
                ])

                busy_blocks = [
                    {'start': row['start_time'], 'end': row['end_time']}
                    for row in busy_result
                ]

                # Get member's existing bookings
                bookings_query = """
                    SELECT start_time, end_time
                    FROM bookings
                    WHERE host_user_id = $1
                      AND start_time < $2
                      AND end_time > $3
                      AND status IN ('pending', 'confirmed')
                """
                bookings_result = await self.dal.execute(bookings_query, [
                    user_id, day_end, check_date
                ])

                booked_slots = [
                    {'start': row['start_time'], 'end': row['end_time']}
                    for row in bookings_result
                ]

                # Filter candidate slots for this member
                available_for_member = []
                for slot in candidate_slots:
                    is_available = True

                    for busy in busy_blocks:
                        if self._slots_overlap(slot, busy):
                            is_available = False
                            break

                    if is_available:
                        for booked in booked_slots:
                            if self._slots_overlap(slot, booked):
                                is_available = False
                                break

                    if is_available:
                        available_for_member.append(slot)

                member_slots[user_id] = available_for_member

            # Step 4: Find common slots and aggregate counts
            # Collect all unique slot times
            all_slot_times = set()
            for slots in member_slots.values():
                for slot in slots:
                    slot_key = (slot['start'], slot['end'])
                    all_slot_times.add(slot_key)

            # For each unique slot, count member availability
            aggregated_slots = []
            for slot_start, slot_end in sorted(all_slot_times):
                available_count = 0
                unavailable_count = 0
                required_available = 0
                required_total = len(required_members)

                for member in members:
                    user_id = member['user_id']
                    is_required = member['is_required']

                    # Check if member is available for this slot
                    member_available = any(
                        s['start'] == slot_start and s['end'] == slot_end
                        for s in member_slots.get(user_id, [])
                    )

                    if member_available:
                        available_count += 1
                        if is_required:
                            required_available += 1
                    else:
                        unavailable_count += 1

                # Only include slots where all required members are available
                meets_requirements = (required_available == required_total)

                if meets_requirements:
                    aggregated_slots.append({
                        'start': slot_start.isoformat(),
                        'end': slot_end.isoformat(),
                        'available_count': available_count,
                        'maybe_count': 0,  # Not tracking tentative in this version
                        'unavailable_count': unavailable_count,
                        'meets_requirements': True
                    })

            return aggregated_slots

        except Exception as e:
            logger.error(f"[ERROR] Failed to get group availability: {e}")
            return []

    def _slots_overlap(self, slot1: Dict, slot2: Dict) -> bool:
        """
        Check if two time slots overlap.

        Args:
            slot1: Dict with 'start' and 'end' datetime objects
            slot2: Dict with 'start' and 'end' datetime objects

        Returns:
            True if slots overlap, False otherwise
        """
        return slot1['start'] < slot2['end'] and slot1['end'] > slot2['start']

    async def get_most_available_slots(
        self,
        page_id: int,
        date_range_start: datetime,
        date_range_end: datetime,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the N most available slots across a date range.

        Args:
            page_id: Group booking page ID
            date_range_start: Start of date range
            date_range_end: End of date range
            limit: Number of top slots to return (default 5)

        Returns:
            List of top N slot dicts sorted by availability (highest first)
        """
        try:
            # Collect slots across all dates in range
            all_slots = []
            current_date = date_range_start.replace(hour=0, minute=0, second=0, microsecond=0)
            range_end = date_range_end.replace(hour=0, minute=0, second=0, microsecond=0)

            while current_date <= range_end:
                day_slots = await self.get_group_availability(page_id, current_date)
                all_slots.extend(day_slots)
                current_date += timedelta(days=1)

            # Sort by available_count (descending)
            all_slots.sort(key=lambda s: s['available_count'], reverse=True)

            # Return top N
            return all_slots[:limit]

        except Exception as e:
            logger.error(f"[ERROR] Failed to get most available slots: {e}")
            return []
