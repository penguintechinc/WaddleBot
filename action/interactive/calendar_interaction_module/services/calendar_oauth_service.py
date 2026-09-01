"""
Calendar OAuth Service - Google and Microsoft Calendar OAuth + Free/Busy Sync
Handles OAuth flows, token management, and free/busy synchronization
"""
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

import httpx

logger = logging.getLogger(__name__)

# OAuth Configuration
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
GOOGLE_FREEBUSY_URL = "https://www.googleapis.com/calendar/v3/freeBusy"

MICROSOFT_AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
MICROSOFT_TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
MICROSOFT_CALENDAR_SCOPE = "Calendars.Read"
MICROSOFT_SCHEDULE_URL = "https://graph.microsoft.com/v1.0/me/calendar/getSchedule"


class CalendarOAuthService:
    """
    Service for managing Google Calendar and Microsoft Calendar OAuth connections.

    Features:
    - OAuth 2.0 authorization flows
    - Token exchange and refresh
    - Free/busy synchronization
    - Token expiry management
    - Calendar connection management
    """

    def __init__(self, dal):
        """
        Initialize OAuth service with database abstraction layer.

        Args:
            dal: AsyncDAL database abstraction layer
        """
        self.dal = dal
        self.google_client_id = os.getenv('GOOGLE_CALENDAR_CLIENT_ID', '')
        self.google_client_secret = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET', '')
        self.microsoft_client_id = os.getenv('MICROSOFT_CALENDAR_CLIENT_ID', '')
        self.microsoft_client_secret = os.getenv('MICROSOFT_CALENDAR_CLIENT_SECRET', '')

    async def get_google_auth_url(
        self,
        user_id: int,
        redirect_uri: str
    ) -> str:
        """
        Generate Google Calendar OAuth authorization URL.

        Args:
            user_id: Hub user ID
            redirect_uri: OAuth callback URL

        Returns:
            Authorization URL for user to visit
        """
        params = {
            'client_id': self.google_client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': GOOGLE_CALENDAR_SCOPE,
            'access_type': 'offline',
            'prompt': 'consent',
            'state': str(user_id)
        }

        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        logger.info(f"[OAUTH] Generated Google auth URL for user={user_id}")
        return auth_url

    async def get_microsoft_auth_url(
        self,
        user_id: int,
        redirect_uri: str
    ) -> str:
        """
        Generate Microsoft Calendar OAuth authorization URL.

        Args:
            user_id: Hub user ID
            redirect_uri: OAuth callback URL

        Returns:
            Authorization URL for user to visit
        """
        params = {
            'client_id': self.microsoft_client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': MICROSOFT_CALENDAR_SCOPE,
            'response_mode': 'query',
            'state': str(user_id)
        }

        auth_url = f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"
        logger.info(f"[OAUTH] Generated Microsoft auth URL for user={user_id}")
        return auth_url

    async def handle_google_callback(
        self,
        user_id: int,
        code: str,
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle Google OAuth callback and exchange code for tokens.

        Args:
            user_id: Hub user ID
            code: Authorization code from OAuth callback
            redirect_uri: OAuth callback URL (must match auth request)

        Returns:
            Connected calendar record or None on failure
        """
        try:
            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        'code': code,
                        'client_id': self.google_client_id,
                        'client_secret': self.google_client_secret,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                )

                if response.status_code != 200:
                    logger.error(
                        f"[OAUTH] Google token exchange failed: {response.status_code} "
                        f"{response.text}"
                    )
                    return None

                token_data = response.json()

            # Store tokens in platform_integrations
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            query = """
                INSERT INTO platform_integrations (
                    hub_user_id, platform, integration_type,
                    access_token, refresh_token, token_expires_at,
                    is_active, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING id
            """

            result = await self.dal.execute(query, [
                user_id, 'google_calendar', 'user_oauth',
                access_token, refresh_token, expires_at, True
            ])

            if not result:
                logger.error(f"[OAUTH] Failed to store Google tokens for user={user_id}")
                return None

            platform_integration_id = result[0]['id']

            # Create connected_calendar entry
            # For now, use 'primary' as calendar_id
            calendar_query = """
                INSERT INTO connected_calendars (
                    hub_user_id, platform_integration_id, provider,
                    calendar_id, calendar_name, is_primary, sync_enabled
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, provider, calendar_id, calendar_name, is_primary
            """

            calendar_result = await self.dal.execute(calendar_query, [
                user_id, platform_integration_id, 'google',
                'primary', 'Google Calendar', True, True
            ])

            if not calendar_result:
                logger.error(
                    f"[OAUTH] Failed to create connected_calendar for user={user_id}"
                )
                return None

            connected_calendar = calendar_result[0]

            logger.info(
                f"[AUDIT] Google Calendar connected: user={user_id}, "
                f"calendar_id={connected_calendar['id']}"
            )

            return {
                'id': connected_calendar['id'],
                'provider': connected_calendar['provider'],
                'calendar_id': connected_calendar['calendar_id'],
                'calendar_name': connected_calendar['calendar_name'],
                'is_primary': connected_calendar['is_primary']
            }

        except Exception as e:
            logger.error(f"[OAUTH] Google callback error for user={user_id}: {e}")
            return None

    async def handle_microsoft_callback(
        self,
        user_id: int,
        code: str,
        redirect_uri: str
    ) -> Optional[Dict[str, Any]]:
        """
        Handle Microsoft OAuth callback and exchange code for tokens.

        Args:
            user_id: Hub user ID
            code: Authorization code from OAuth callback
            redirect_uri: OAuth callback URL (must match auth request)

        Returns:
            Connected calendar record or None on failure
        """
        try:
            # Exchange code for tokens
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    MICROSOFT_TOKEN_URL,
                    data={
                        'code': code,
                        'client_id': self.microsoft_client_id,
                        'client_secret': self.microsoft_client_secret,
                        'redirect_uri': redirect_uri,
                        'grant_type': 'authorization_code'
                    }
                )

                if response.status_code != 200:
                    logger.error(
                        f"[OAUTH] Microsoft token exchange failed: {response.status_code} "
                        f"{response.text}"
                    )
                    return None

                token_data = response.json()

            # Store tokens in platform_integrations
            access_token = token_data.get('access_token')
            refresh_token = token_data.get('refresh_token')
            expires_in = token_data.get('expires_in', 3600)
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            query = """
                INSERT INTO platform_integrations (
                    hub_user_id, platform, integration_type,
                    access_token, refresh_token, token_expires_at,
                    is_active, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
                RETURNING id
            """

            result = await self.dal.execute(query, [
                user_id, 'microsoft_calendar', 'user_oauth',
                access_token, refresh_token, expires_at, True
            ])

            if not result:
                logger.error(
                    f"[OAUTH] Failed to store Microsoft tokens for user={user_id}"
                )
                return None

            platform_integration_id = result[0]['id']

            # Create connected_calendar entry
            calendar_query = """
                INSERT INTO connected_calendars (
                    hub_user_id, platform_integration_id, provider,
                    calendar_id, calendar_name, is_primary, sync_enabled
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, provider, calendar_id, calendar_name, is_primary
            """

            calendar_result = await self.dal.execute(calendar_query, [
                user_id, platform_integration_id, 'microsoft',
                'default', 'Microsoft Calendar', True, True
            ])

            if not calendar_result:
                logger.error(
                    f"[OAUTH] Failed to create connected_calendar for user={user_id}"
                )
                return None

            connected_calendar = calendar_result[0]

            logger.info(
                f"[AUDIT] Microsoft Calendar connected: user={user_id}, "
                f"calendar_id={connected_calendar['id']}"
            )

            return {
                'id': connected_calendar['id'],
                'provider': connected_calendar['provider'],
                'calendar_id': connected_calendar['calendar_id'],
                'calendar_name': connected_calendar['calendar_name'],
                'is_primary': connected_calendar['is_primary']
            }

        except Exception as e:
            logger.error(f"[OAUTH] Microsoft callback error for user={user_id}: {e}")
            return None

    async def refresh_token_if_needed(
        self,
        platform_integration_id: int
    ) -> bool:
        """
        Check token expiry and refresh if needed.

        Args:
            platform_integration_id: Platform integration ID

        Returns:
            True if token is valid/refreshed, False on failure
        """
        try:
            # Get integration details
            query = """
                SELECT id, platform, access_token, refresh_token, token_expires_at
                FROM platform_integrations
                WHERE id = $1 AND is_active = TRUE
            """

            rows = await self.dal.execute(query, [platform_integration_id])

            if not rows:
                logger.warning(
                    f"[OAUTH] Platform integration not found: id={platform_integration_id}"
                )
                return False

            integration = rows[0]
            expires_at = integration['token_expires_at']

            # Check if token will expire in next 5 minutes
            if expires_at and (expires_at - datetime.now(timezone.utc)) > timedelta(minutes=5):
                # Token still valid
                return True

            # Need to refresh token
            refresh_token = integration['refresh_token']
            if not refresh_token:
                logger.error(
                    f"[OAUTH] No refresh token available for "
                    f"platform_integration_id={platform_integration_id}"
                )
                return False

            platform = integration['platform']

            if platform == 'google_calendar':
                token_url = GOOGLE_TOKEN_URL
                client_id = self.google_client_id
                client_secret = self.google_client_secret
            elif platform == 'microsoft_calendar':
                token_url = MICROSOFT_TOKEN_URL
                client_id = self.microsoft_client_id
                client_secret = self.microsoft_client_secret
            else:
                logger.error(f"[OAUTH] Unknown platform: {platform}")
                return False

            # Refresh the token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        'refresh_token': refresh_token,
                        'client_id': client_id,
                        'client_secret': client_secret,
                        'grant_type': 'refresh_token'
                    }
                )

                if response.status_code != 200:
                    logger.error(
                        f"[OAUTH] Token refresh failed: {response.status_code} "
                        f"{response.text}"
                    )
                    return False

                token_data = response.json()

            # Update tokens in database
            new_access_token = token_data.get('access_token')
            expires_in = token_data.get('expires_in', 3600)
            new_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

            # Some providers may issue new refresh token
            new_refresh_token = token_data.get('refresh_token', refresh_token)

            update_query = """
                UPDATE platform_integrations
                SET access_token = $1, refresh_token = $2,
                    token_expires_at = $3, updated_at = NOW()
                WHERE id = $4
            """

            await self.dal.execute(update_query, [
                new_access_token, new_refresh_token,
                new_expires_at, platform_integration_id
            ])

            logger.info(
                f"[OAUTH] Token refreshed: platform_integration_id={platform_integration_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[OAUTH] Token refresh error for "
                f"platform_integration_id={platform_integration_id}: {e}"
            )
            return False

    async def sync_free_busy(
        self,
        user_id: int,
        calendar_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> bool:
        """
        Fetch free/busy data from external calendar and store in database.

        Args:
            user_id: Hub user ID
            calendar_id: Connected calendar ID
            start_date: Start of time range
            end_date: End of time range

        Returns:
            True on success, False on failure
        """
        try:
            # Get calendar and integration details
            query = """
                SELECT cc.id, cc.provider, cc.calendar_id, cc.platform_integration_id,
                       pi.access_token
                FROM connected_calendars cc
                JOIN platform_integrations pi ON cc.platform_integration_id = pi.id
                WHERE cc.id = $1 AND cc.hub_user_id = $2 AND cc.sync_enabled = TRUE
            """

            rows = await self.dal.execute(query, [calendar_id, user_id])

            if not rows:
                logger.warning(
                    f"[SYNC] Calendar not found or sync disabled: "
                    f"calendar_id={calendar_id}, user={user_id}"
                )
                return False

            calendar = rows[0]
            provider = calendar['provider']
            access_token = calendar['access_token']
            platform_integration_id = calendar['platform_integration_id']

            # Refresh token if needed
            await self.refresh_token_if_needed(platform_integration_id)

            # Re-fetch access token in case it was refreshed
            token_query = """
                SELECT access_token FROM platform_integrations WHERE id = $1
            """
            token_rows = await self.dal.execute(token_query, [platform_integration_id])
            if token_rows:
                access_token = token_rows[0]['access_token']

            # Fetch free/busy data based on provider
            busy_times = []

            async with httpx.AsyncClient() as client:
                if provider == 'google':
                    busy_times = await self._fetch_google_freebusy(
                        client, access_token, calendar['calendar_id'],
                        start_date, end_date
                    )
                elif provider == 'microsoft':
                    busy_times = await self._fetch_microsoft_schedule(
                        client, access_token, start_date, end_date
                    )
                else:
                    logger.error(f"[SYNC] Unknown provider: {provider}")
                    return False

            # Delete old free/busy entries for this time range
            delete_query = """
                DELETE FROM calendar_free_busy
                WHERE connected_calendar_id = $1
                  AND start_time >= $2 AND end_time <= $3
            """
            await self.dal.execute(delete_query, [calendar_id, start_date, end_date])

            # Insert new free/busy entries
            for busy_block in busy_times:
                insert_query = """
                    INSERT INTO calendar_free_busy (
                        hub_user_id, connected_calendar_id,
                        start_time, end_time, status, fetched_at
                    )
                    VALUES ($1, $2, $3, $4, $5, NOW())
                """
                await self.dal.execute(insert_query, [
                    user_id, calendar_id,
                    busy_block['start'], busy_block['end'],
                    busy_block.get('status', 'busy')
                ])

            # Update last_sync_at
            update_query = """
                UPDATE connected_calendars
                SET last_sync_at = NOW(), sync_error = NULL
                WHERE id = $1
            """
            await self.dal.execute(update_query, [calendar_id])

            logger.info(
                f"[SYNC] Free/busy synced: calendar_id={calendar_id}, "
                f"blocks={len(busy_times)}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[SYNC] Free/busy sync error: calendar_id={calendar_id}, "
                f"user={user_id}, error={e}"
            )

            # Store error in connected_calendars
            error_query = """
                UPDATE connected_calendars
                SET sync_error = $1
                WHERE id = $2
            """
            await self.dal.execute(error_query, [str(e), calendar_id])

            return False

    async def _fetch_google_freebusy(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        calendar_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch free/busy from Google Calendar API."""
        request_body = {
            'timeMin': start_date.isoformat(),
            'timeMax': end_date.isoformat(),
            'items': [{'id': calendar_id}]
        }

        response = await client.post(
            GOOGLE_FREEBUSY_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            json=request_body
        )

        if response.status_code != 200:
            logger.error(
                f"[SYNC] Google free/busy fetch failed: {response.status_code} "
                f"{response.text}"
            )
            return []

        data = response.json()
        busy_times = []

        for item in data.get('calendars', {}).get(calendar_id, {}).get('busy', []):
            busy_times.append({
                'start': datetime.fromisoformat(item['start'].replace('Z', '+00:00')),
                'end': datetime.fromisoformat(item['end'].replace('Z', '+00:00')),
                'status': 'busy'
            })

        return busy_times

    async def _fetch_microsoft_schedule(
        self,
        client: httpx.AsyncClient,
        access_token: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Fetch schedule from Microsoft Graph API."""
        request_body = {
            'schedules': ['me'],
            'startTime': {
                'dateTime': start_date.isoformat(),
                'timeZone': 'UTC'
            },
            'endTime': {
                'dateTime': end_date.isoformat(),
                'timeZone': 'UTC'
            },
            'availabilityViewInterval': 30
        }

        response = await client.post(
            MICROSOFT_SCHEDULE_URL,
            headers={'Authorization': f'Bearer {access_token}'},
            json=request_body
        )

        if response.status_code != 200:
            logger.error(
                f"[SYNC] Microsoft schedule fetch failed: {response.status_code} "
                f"{response.text}"
            )
            return []

        data = response.json()
        busy_times = []

        for schedule in data.get('value', []):
            for item in schedule.get('scheduleItems', []):
                if item.get('status') in ['busy', 'tentative']:
                    busy_times.append({
                        'start': datetime.fromisoformat(
                            item['start']['dateTime'].replace('Z', '+00:00')
                        ),
                        'end': datetime.fromisoformat(
                            item['end']['dateTime'].replace('Z', '+00:00')
                        ),
                        'status': item['status']
                    })

        return busy_times

    async def disconnect_calendar(
        self,
        user_id: int,
        calendar_id: int
    ) -> bool:
        """
        Disconnect a calendar and deactivate platform integration.

        Args:
            user_id: Hub user ID
            calendar_id: Connected calendar ID

        Returns:
            True on success, False on failure
        """
        try:
            # Get platform_integration_id
            query = """
                SELECT platform_integration_id
                FROM connected_calendars
                WHERE id = $1 AND hub_user_id = $2
            """

            rows = await self.dal.execute(query, [calendar_id, user_id])

            if not rows:
                logger.warning(
                    f"[OAUTH] Calendar not found: calendar_id={calendar_id}, "
                    f"user={user_id}"
                )
                return False

            platform_integration_id = rows[0]['platform_integration_id']

            # Deactivate connected_calendar
            update_calendar = """
                UPDATE connected_calendars
                SET sync_enabled = FALSE, updated_at = NOW()
                WHERE id = $1
            """
            await self.dal.execute(update_calendar, [calendar_id])

            # Deactivate platform_integration
            update_integration = """
                UPDATE platform_integrations
                SET is_active = FALSE, updated_at = NOW()
                WHERE id = $1
            """
            await self.dal.execute(update_integration, [platform_integration_id])

            logger.info(
                f"[AUDIT] Calendar disconnected: calendar_id={calendar_id}, "
                f"user={user_id}"
            )
            return True

        except Exception as e:
            logger.error(
                f"[OAUTH] Disconnect error: calendar_id={calendar_id}, "
                f"user={user_id}, error={e}"
            )
            return False

    async def list_connected_calendars(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get list of connected calendars for a user.

        Args:
            user_id: Hub user ID

        Returns:
            List of connected calendar records
        """
        try:
            query = """
                SELECT id, provider, calendar_id, calendar_name, is_primary,
                       sync_enabled, last_sync_at, sync_error, created_at
                FROM connected_calendars
                WHERE hub_user_id = $1
                ORDER BY is_primary DESC, created_at ASC
            """

            rows = await self.dal.execute(query, [user_id])

            calendars = []
            for row in rows:
                calendars.append({
                    'id': row['id'],
                    'provider': row['provider'],
                    'calendar_id': row['calendar_id'],
                    'calendar_name': row['calendar_name'],
                    'is_primary': row['is_primary'],
                    'sync_enabled': row['sync_enabled'],
                    'last_sync_at': row['last_sync_at'].isoformat() if row['last_sync_at'] else None,
                    'sync_error': row['sync_error'],
                    'created_at': row['created_at'].isoformat()
                })

            return calendars

        except Exception as e:
            logger.error(
                f"[OAUTH] List calendars error for user={user_id}: {e}"
            )
            return []
