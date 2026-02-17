"""
Booking Service - Individual appointment scheduling and management

Handles appointment booking functionality:
- Individual booking page creation and management
- Slot availability calculation based on user calendar settings
- Booking creation with race condition protection
- Booking cancellation and completion
- Host availability integration with free/busy data
"""
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BookingService:
    """
    Booking service for individual appointment scheduling.

    Features:
    - Individual booking page CRUD operations
    - Available slot calculation with min_notice and max_future constraints
    - Booking creation with FOR UPDATE locking for race condition protection
    - Booking cancellation and status management
    - Integration with user_calendar_settings and calendar_free_busy
    """

    def __init__(self, dal):
        """
        Initialize booking service with database abstraction layer.

        Args:
            dal: Database abstraction layer
        """
        self.dal = dal

    async def create_booking_page(
        self,
        user_id: int,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create an individual booking page.

        Args:
            user_id: Hub user ID (page owner)
            data: Booking page configuration with keys:
                - slug: URL slug (unique)
                - title: Page title
                - description: Page description
                - slot_duration: Duration in minutes (default 30)
                - access_scope: 'public', 'registered', 'community' (default 'public')
                - form_fields: Optional custom form fields (max 8)

        Returns:
            Booking page dict or None on failure
        """
        try:
            query = """
                INSERT INTO booking_pages (
                    slug, page_type, hub_user_id, title, description,
                    slot_duration, access_scope, form_fields
                )
                VALUES ($1, 'individual', $2, $3, $4, $5, $6, $7)
                RETURNING id, slug, title, description, slot_duration,
                          access_scope, form_fields, created_at
            """
            result = await self.dal.execute(query, [
                data.get('slug'),
                user_id,
                data.get('title'),
                data.get('description'),
                data.get('slot_duration', 30),
                data.get('access_scope', 'public'),
                data.get('form_fields', [])
            ])

            if result and len(result) > 0:
                row = result[0]
                logger.info(
                    f"[AUDIT] Booking page created: id={row['id']}, "
                    f"slug={row['slug']}, user={user_id}"
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
            logger.error(f"[ERROR] Failed to create booking page: {e}")
            return None

    async def update_booking_page(
        self,
        page_id: int,
        user_id: int,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a booking page (owner only).

        Args:
            page_id: Booking page ID
            user_id: Hub user ID (must be page owner)
            data: Updates to apply

        Returns:
            Updated booking page dict or None on failure
        """
        try:
            # Build dynamic UPDATE query for provided fields
            update_fields = []
            params = []
            param_idx = 1

            allowed_fields = ['title', 'description', 'slot_duration',
                              'access_scope', 'form_fields', 'is_active']

            for field in allowed_fields:
                if field in data:
                    update_fields.append(f"{field} = ${param_idx}")
                    params.append(data[field])
                    param_idx += 1

            if not update_fields:
                # No fields to update
                return await self.get_booking_page(page_id)

            params.extend([page_id, user_id])

            query = f"""
                UPDATE booking_pages
                SET {', '.join(update_fields)}, updated_at = NOW()
                WHERE id = ${param_idx} AND hub_user_id = ${param_idx + 1}
                RETURNING id, slug, title, description, slot_duration,
                          access_scope, form_fields, is_active, updated_at
            """
            result = await self.dal.execute(query, params)

            if result and len(result) > 0:
                row = result[0]
                logger.info(
                    f"[AUDIT] Booking page updated: id={row['id']}, "
                    f"slug={row['slug']}, user={user_id}"
                )
                return {
                    'id': row['id'],
                    'slug': row['slug'],
                    'title': row['title'],
                    'description': row['description'],
                    'slot_duration': row['slot_duration'],
                    'access_scope': row['access_scope'],
                    'form_fields': row['form_fields'],
                    'is_active': row['is_active'],
                    'updated_at': row['updated_at'].isoformat()
                }
            return None

        except Exception as e:
            logger.error(f"[ERROR] Failed to update booking page: {e}")
            return None

    async def get_booking_page(
        self,
        slug_or_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get booking page by slug or ID.

        Args:
            slug_or_id: Booking page slug (string) or ID (numeric string)

        Returns:
            Booking page dict or None if not found
        """
        try:
            # Determine if input is numeric ID or slug
            try:
                page_id = int(slug_or_id)
                query = """
                    SELECT id, slug, page_type, hub_user_id, community_id, title,
                           description, slot_duration, access_scope, form_fields,
                           is_active, created_at, updated_at
                    FROM booking_pages
                    WHERE id = $1 AND is_active = TRUE
                """
                params = [page_id]
            except ValueError:
                # It's a slug
                query = """
                    SELECT id, slug, page_type, hub_user_id, community_id, title,
                           description, slot_duration, access_scope, form_fields,
                           is_active, created_at, updated_at
                    FROM booking_pages
                    WHERE slug = $1 AND is_active = TRUE
                """
                params = [slug_or_id]

            result = await self.dal.execute(query, params)

            if result and len(result) > 0:
                row = result[0]
                return {
                    'id': row['id'],
                    'slug': row['slug'],
                    'page_type': row['page_type'],
                    'hub_user_id': row['hub_user_id'],
                    'community_id': row['community_id'],
                    'title': row['title'],
                    'description': row['description'],
                    'slot_duration': row['slot_duration'],
                    'access_scope': row['access_scope'],
                    'form_fields': row['form_fields'],
                    'is_active': row['is_active'],
                    'created_at': row['created_at'].isoformat(),
                    'updated_at': row['updated_at'].isoformat()
                }
            return None

        except Exception as e:
            logger.error(f"[ERROR] Failed to get booking page: {e}")
            return None

    async def list_user_booking_pages(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        List all booking pages for a user.

        Args:
            user_id: Hub user ID

        Returns:
            List of booking page dicts
        """
        try:
            query = """
                SELECT id, slug, title, description, slot_duration,
                       access_scope, is_active, created_at
                FROM booking_pages
                WHERE hub_user_id = $1 AND page_type = 'individual'
                ORDER BY created_at DESC
            """
            result = await self.dal.execute(query, [user_id])

            pages = []
            for row in result:
                pages.append({
                    'id': row['id'],
                    'slug': row['slug'],
                    'title': row['title'],
                    'description': row['description'],
                    'slot_duration': row['slot_duration'],
                    'access_scope': row['access_scope'],
                    'is_active': row['is_active'],
                    'created_at': row['created_at'].isoformat()
                })

            return pages

        except Exception as e:
            logger.error(f"[ERROR] Failed to list booking pages: {e}")
            return []

    async def delete_booking_page(
        self,
        page_id: int,
        user_id: int
    ) -> bool:
        """
        Soft-delete a booking page (owner only).

        Args:
            page_id: Booking page ID
            user_id: Hub user ID (must be page owner)

        Returns:
            True on success, False on failure
        """
        try:
            query = """
                UPDATE booking_pages
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = $1 AND hub_user_id = $2 AND page_type = 'individual'
                RETURNING id
            """
            result = await self.dal.execute(query, [page_id, user_id])

            if result and len(result) > 0:
                logger.info(
                    f"[AUDIT] Booking page deleted: id={page_id}, user={user_id}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to delete booking page: {e}")
            return False

    async def get_available_slots(
        self,
        booking_page_id: int,
        date: datetime
    ) -> List[Dict[str, Any]]:
        """
        Calculate available booking slots for a specific date.

        Logic:
        1. Get booking page config (slot_duration)
        2. Get host's availability settings (weekly_availability, min_notice, max_future)
        3. Get host's free/busy blocks for the date
        4. Generate slots based on weekly_availability
        5. Remove slots that conflict with free/busy blocks
        6. Remove slots that conflict with existing confirmed bookings
        7. Apply min_notice and max_future constraints
        8. Return list of available slots

        Args:
            booking_page_id: Booking page ID
            date: Date to check (datetime object, time component ignored)

        Returns:
            List of slot dicts with 'start' and 'end' ISO timestamps
        """
        try:
            # Step 1: Get booking page and host
            page_query = """
                SELECT hub_user_id, slot_duration
                FROM booking_pages
                WHERE id = $1 AND is_active = TRUE AND page_type = 'individual'
            """
            page_result = await self.dal.execute(page_query, [booking_page_id])

            if not page_result or len(page_result) == 0:
                logger.warning(f"Booking page {booking_page_id} not found")
                return []

            host_user_id = page_result[0]['hub_user_id']
            slot_duration = page_result[0]['slot_duration']

            # Step 2: Get host's calendar settings
            settings_query = """
                SELECT weekly_availability, timezone, min_notice_hours,
                       max_future_days, buffer_minutes
                FROM user_calendar_settings
                WHERE hub_user_id = $1
            """
            settings_result = await self.dal.execute(settings_query, [host_user_id])

            if not settings_result or len(settings_result) == 0:
                logger.warning(f"No calendar settings for user {host_user_id}")
                return []

            settings = settings_result[0]
            weekly_availability = settings.get('weekly_availability', {})
            tz = settings.get('timezone', 'UTC')
            min_notice_hours = settings.get('min_notice_hours', 4)
            max_future_days = settings.get('max_future_days', 30)
            buffer_minutes = settings.get('buffer_minutes', 0)

            # Step 3: Apply min_notice and max_future constraints
            now = datetime.now(timezone.utc)
            earliest_slot = now + timedelta(hours=min_notice_hours)
            latest_slot = now + timedelta(days=max_future_days)

            # Normalize date to start of day in UTC
            check_date = date.replace(hour=0, minute=0, second=0, microsecond=0)

            # If entire day is outside the booking window, return empty
            if check_date > latest_slot or check_date + timedelta(days=1) < earliest_slot:
                return []

            # Step 4: Get day of week and generate slots from weekly_availability
            day_name = check_date.strftime('%A').lower()
            day_availability = weekly_availability.get(day_name, [])

            if not day_availability:
                # No availability for this day
                return []

            # Generate slots for each availability block
            candidate_slots = []
            for block in day_availability:
                start_time_str = block.get('start')  # e.g., "09:00"
                end_time_str = block.get('end')      # e.g., "17:00"

                if not start_time_str or not end_time_str:
                    continue

                # Parse times
                start_hour, start_minute = map(int, start_time_str.split(':'))
                end_hour, end_minute = map(int, end_time_str.split(':'))

                block_start = check_date.replace(hour=start_hour, minute=start_minute)
                block_end = check_date.replace(hour=end_hour, minute=end_minute)

                # Generate slots within this block
                current = block_start
                while current + timedelta(minutes=slot_duration) <= block_end:
                    slot_end = current + timedelta(minutes=slot_duration)

                    # Apply min_notice and max_future constraints
                    if current >= earliest_slot and current <= latest_slot:
                        candidate_slots.append({
                            'start': current,
                            'end': slot_end
                        })

                    current = slot_end + timedelta(minutes=buffer_minutes)

            # Step 5: Get free/busy blocks for the date
            busy_query = """
                SELECT start_time, end_time
                FROM calendar_free_busy
                WHERE hub_user_id = $1
                  AND start_time < $2
                  AND end_time > $3
                  AND status IN ('busy', 'tentative')
            """
            day_end = check_date + timedelta(days=1)
            busy_result = await self.dal.execute(busy_query, [
                host_user_id, day_end, check_date
            ])

            busy_blocks = []
            for row in busy_result:
                busy_blocks.append({
                    'start': row['start_time'],
                    'end': row['end_time']
                })

            # Step 6: Get existing confirmed bookings
            bookings_query = """
                SELECT start_time, end_time
                FROM bookings
                WHERE host_user_id = $1
                  AND start_time < $2
                  AND end_time > $3
                  AND status IN ('pending', 'confirmed')
            """
            bookings_result = await self.dal.execute(bookings_query, [
                host_user_id, day_end, check_date
            ])

            booked_slots = []
            for row in bookings_result:
                booked_slots.append({
                    'start': row['start_time'],
                    'end': row['end_time']
                })

            # Step 7: Filter out conflicting slots
            available_slots = []
            for slot in candidate_slots:
                is_available = True

                # Check against busy blocks
                for busy in busy_blocks:
                    if self._slots_overlap(slot, busy):
                        is_available = False
                        break

                # Check against booked slots
                if is_available:
                    for booked in booked_slots:
                        if self._slots_overlap(slot, booked):
                            is_available = False
                            break

                if is_available:
                    available_slots.append({
                        'start': slot['start'].isoformat(),
                        'end': slot['end'].isoformat()
                    })

            return available_slots

        except Exception as e:
            logger.error(f"[ERROR] Failed to get available slots: {e}")
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

    async def create_booking(
        self,
        booking_page_id: int,
        guest_data: Dict[str, Any],
        slot_start: datetime,
        slot_end: datetime,
        form_responses: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Create a booking with race condition protection.

        Args:
            booking_page_id: Booking page ID
            guest_data: Guest information with keys:
                - guest_user_id: Optional hub user ID
                - guest_name: Guest's name
                - guest_email: Optional guest email
            slot_start: Booking start time
            slot_end: Booking end time
            form_responses: Optional custom form responses

        Returns:
            Booking dict with booking_uuid or None on failure
        """
        try:
            # Get booking page and host
            page_query = """
                SELECT hub_user_id FROM booking_pages
                WHERE id = $1 AND is_active = TRUE AND page_type = 'individual'
                FOR UPDATE
            """
            page_result = await self.dal.execute(page_query, [booking_page_id])

            if not page_result or len(page_result) == 0:
                logger.warning(f"Booking page {booking_page_id} not found")
                return None

            host_user_id = page_result[0]['hub_user_id']

            # Check for conflicting bookings with FOR UPDATE lock
            conflict_query = """
                SELECT id FROM bookings
                WHERE host_user_id = $1
                  AND start_time < $2
                  AND end_time > $3
                  AND status IN ('pending', 'confirmed')
                FOR UPDATE
            """
            conflict_result = await self.dal.execute(conflict_query, [
                host_user_id, slot_end, slot_start
            ])

            if conflict_result and len(conflict_result) > 0:
                logger.warning(
                    f"Slot conflict detected for host {host_user_id}: "
                    f"{slot_start} - {slot_end}"
                )
                return None

            # Create booking
            booking_uuid = str(uuid.uuid4())
            insert_query = """
                INSERT INTO bookings (
                    booking_uuid, booking_page_id, host_user_id,
                    guest_user_id, guest_name, guest_email,
                    start_time, end_time, timezone, status, form_responses
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id, booking_uuid, start_time, end_time, status, created_at
            """
            result = await self.dal.execute(insert_query, [
                booking_uuid,
                booking_page_id,
                host_user_id,
                guest_data.get('guest_user_id'),
                guest_data.get('guest_name'),
                guest_data.get('guest_email'),
                slot_start,
                slot_end,
                'UTC',
                'confirmed',
                form_responses or {}
            ])

            if result and len(result) > 0:
                row = result[0]
                logger.info(
                    f"[AUDIT] Booking created: uuid={row['booking_uuid']}, "
                    f"host={host_user_id}, guest={guest_data.get('guest_name')}"
                )
                return {
                    'id': row['id'],
                    'booking_uuid': row['booking_uuid'],
                    'host_user_id': host_user_id,
                    'guest_name': guest_data.get('guest_name'),
                    'guest_email': guest_data.get('guest_email'),
                    'start_time': row['start_time'].isoformat(),
                    'end_time': row['end_time'].isoformat(),
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat()
                }
            return None

        except Exception as e:
            logger.error(f"[ERROR] Failed to create booking: {e}")
            return None

    async def cancel_booking(
        self,
        booking_uuid: str,
        cancelled_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """
        Cancel a booking.

        Args:
            booking_uuid: Booking UUID
            cancelled_by: 'host' or 'guest'
            reason: Optional cancellation reason

        Returns:
            True on success, False on failure
        """
        try:
            status_map = {
                'host': 'cancelled_by_host',
                'guest': 'cancelled_by_guest'
            }

            new_status = status_map.get(cancelled_by, 'cancelled_by_guest')

            query = """
                UPDATE bookings
                SET status = $1, cancelled_at = NOW(),
                    cancellation_reason = $2, updated_at = NOW()
                WHERE booking_uuid = $3
                  AND status IN ('pending', 'confirmed')
                RETURNING id, booking_uuid
            """
            result = await self.dal.execute(query, [
                new_status, reason, booking_uuid
            ])

            if result and len(result) > 0:
                logger.info(
                    f"[AUDIT] Booking cancelled: uuid={booking_uuid}, "
                    f"by={cancelled_by}, reason={reason}"
                )
                return True
            return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to cancel booking: {e}")
            return False

    async def get_booking(
        self,
        booking_uuid: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get booking details by UUID.

        Args:
            booking_uuid: Booking UUID

        Returns:
            Booking dict or None if not found
        """
        try:
            query = """
                SELECT b.id, b.booking_uuid, b.booking_page_id,
                       b.host_user_id, b.guest_user_id, b.guest_name,
                       b.guest_email, b.start_time, b.end_time,
                       b.timezone, b.status, b.form_responses,
                       b.cancelled_at, b.cancellation_reason,
                       b.host_notes, b.guest_notes, b.created_at,
                       bp.title as page_title, bp.slug as page_slug
                FROM bookings b
                JOIN booking_pages bp ON b.booking_page_id = bp.id
                WHERE b.booking_uuid = $1
            """
            result = await self.dal.execute(query, [booking_uuid])

            if result and len(result) > 0:
                row = result[0]
                return {
                    'id': row['id'],
                    'booking_uuid': row['booking_uuid'],
                    'booking_page_id': row['booking_page_id'],
                    'page_title': row['page_title'],
                    'page_slug': row['page_slug'],
                    'host_user_id': row['host_user_id'],
                    'guest_user_id': row['guest_user_id'],
                    'guest_name': row['guest_name'],
                    'guest_email': row['guest_email'],
                    'start_time': row['start_time'].isoformat(),
                    'end_time': row['end_time'].isoformat(),
                    'timezone': row['timezone'],
                    'status': row['status'],
                    'form_responses': row['form_responses'],
                    'cancelled_at': row['cancelled_at'].isoformat() if row['cancelled_at'] else None,
                    'cancellation_reason': row['cancellation_reason'],
                    'host_notes': row['host_notes'],
                    'guest_notes': row['guest_notes'],
                    'created_at': row['created_at'].isoformat()
                }
            return None

        except Exception as e:
            logger.error(f"[ERROR] Failed to get booking: {e}")
            return None

    async def list_host_bookings(
        self,
        user_id: int,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        List bookings for a host with optional filters.

        Args:
            user_id: Host user ID
            status: Optional status filter
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of booking dicts
        """
        try:
            conditions = ["host_user_id = $1"]
            params = [user_id]
            param_idx = 2

            if status:
                conditions.append(f"status = ${param_idx}")
                params.append(status)
                param_idx += 1

            if start_date:
                conditions.append(f"start_time >= ${param_idx}")
                params.append(start_date)
                param_idx += 1

            if end_date:
                conditions.append(f"start_time <= ${param_idx}")
                params.append(end_date)
                param_idx += 1

            query = f"""
                SELECT b.id, b.booking_uuid, b.guest_name, b.guest_email,
                       b.start_time, b.end_time, b.status, b.created_at,
                       bp.title as page_title, bp.slug as page_slug
                FROM bookings b
                JOIN booking_pages bp ON b.booking_page_id = bp.id
                WHERE {' AND '.join(conditions)}
                ORDER BY b.start_time ASC
            """
            result = await self.dal.execute(query, params)

            bookings = []
            for row in result:
                bookings.append({
                    'id': row['id'],
                    'booking_uuid': row['booking_uuid'],
                    'page_title': row['page_title'],
                    'page_slug': row['page_slug'],
                    'guest_name': row['guest_name'],
                    'guest_email': row['guest_email'],
                    'start_time': row['start_time'].isoformat(),
                    'end_time': row['end_time'].isoformat(),
                    'status': row['status'],
                    'created_at': row['created_at'].isoformat()
                })

            return bookings

        except Exception as e:
            logger.error(f"[ERROR] Failed to list host bookings: {e}")
            return []

    async def complete_booking(
        self,
        booking_uuid: str
    ) -> bool:
        """
        Mark booking as completed (after end_time passes).

        Args:
            booking_uuid: Booking UUID

        Returns:
            True on success, False on failure
        """
        try:
            query = """
                UPDATE bookings
                SET status = 'completed', updated_at = NOW()
                WHERE booking_uuid = $1
                  AND status = 'confirmed'
                  AND end_time < NOW()
                RETURNING id
            """
            result = await self.dal.execute(query, [booking_uuid])

            if result and len(result) > 0:
                logger.info(f"[AUDIT] Booking completed: uuid={booking_uuid}")
                return True
            return False

        except Exception as e:
            logger.error(f"[ERROR] Failed to complete booking: {e}")
            return False
