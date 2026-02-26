"""
Provider Service for Server Status Interaction Module

Thin adapter for checking game server status via external APIs.
"""
import logging
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


class ProviderService:
    """Checks game server status through various provider APIs."""

    def __init__(self, config):
        self.config = config
        self.timeout = config.STATUS_CHECK_TIMEOUT

    async def check_steam(self, game_id: str = '730') -> dict:
        """Check Steam/CS2 game server status.

        Args:
            game_id: Steam app ID (default 730 for CS2).

        Returns:
            Status dict with status, details, and checked_at.
        """
        url = (
            'https://api.steampowered.com'
            '/ICSGOServers_730/GetGameServersStatus/v1/'
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                result = data.get('result', {})
                app_info = result.get('app', {})
                status_val = 'online'

                if app_info.get('timestamp'):
                    details = (
                        f"Steam version: {app_info.get('version', 'unknown')}"
                    )
                else:
                    details = 'Steam API returned data'

                matchmaking = result.get('matchmaking', {})
                if matchmaking.get('scheduler') == 'maintenance':
                    status_val = 'degraded'
                    details = 'Matchmaking: maintenance mode'

                return {
                    'status': status_val,
                    'details': details,
                    'checked_at': datetime.now(timezone.utc).isoformat(),
                }
        except httpx.TimeoutException:
            logger.warning("Steam status check timed out")
            return {
                'status': 'offline',
                'details': 'Request timed out',
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error("Steam status check failed: %s", exc)
            return {
                'status': 'offline',
                'details': str(exc),
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }

    async def check_riot(self, region: str = 'na') -> dict:
        """Check Riot Games (LoL) server status.

        Args:
            region: Riot region code (default 'na').

        Returns:
            Status dict with status, details, and checked_at.
        """
        url = (
            f'https://lol.secure.dyn.riotcdn.net'
            f'/channels/public/x/status/{region}.json'
        )
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                incidents = data.get('incidents', [])
                maintenances = data.get('maintenances', [])

                if incidents:
                    titles = [
                        inc.get('titles', [{}])[0].get('content', 'Unknown')
                        for inc in incidents
                        if inc.get('titles')
                    ]
                    return {
                        'status': 'degraded',
                        'details': f"Incidents: {'; '.join(titles)}",
                        'checked_at': datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }

                if maintenances:
                    return {
                        'status': 'degraded',
                        'details': 'Scheduled maintenance in progress',
                        'checked_at': datetime.now(
                            timezone.utc
                        ).isoformat(),
                    }

                return {
                    'status': 'online',
                    'details': 'No active incidents',
                    'checked_at': datetime.now(timezone.utc).isoformat(),
                }
        except httpx.TimeoutException:
            logger.warning("Riot status check timed out for region %s", region)
            return {
                'status': 'offline',
                'details': 'Request timed out',
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error("Riot status check failed: %s", exc)
            return {
                'status': 'offline',
                'details': str(exc),
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }

    async def check_url(self, url: str) -> dict:
        """Check a custom URL for server status.

        Args:
            url: The URL to check via HTTP GET.

        Returns:
            Status dict with status, details, and checked_at.
        """
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                resp = await client.get(url)

                if 200 <= resp.status_code < 300:
                    status_val = 'online'
                    details = f"HTTP {resp.status_code}"
                elif 500 <= resp.status_code < 600:
                    status_val = 'degraded'
                    details = f"HTTP {resp.status_code}"
                else:
                    status_val = 'offline'
                    details = f"HTTP {resp.status_code}"

                return {
                    'status': status_val,
                    'details': details,
                    'checked_at': datetime.now(timezone.utc).isoformat(),
                }
        except httpx.TimeoutException:
            logger.warning("URL status check timed out: %s", url)
            return {
                'status': 'offline',
                'details': 'Request timed out',
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.error("URL status check failed for %s: %s", url, exc)
            return {
                'status': 'offline',
                'details': str(exc),
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }

    async def check(
        self, api_type: str, url: str = None, **kwargs
    ) -> dict:
        """Dispatch status check to appropriate provider.

        Args:
            api_type: One of 'steam', 'riot', or 'custom_url'.
            url: URL for custom_url checks.
            **kwargs: Additional args passed to provider methods.

        Returns:
            Status dict with status, details, and checked_at.
        """
        if api_type == 'steam':
            return await self.check_steam(
                game_id=kwargs.get('game_id', '730')
            )
        elif api_type == 'riot':
            return await self.check_riot(
                region=kwargs.get('region', 'na')
            )
        elif api_type == 'custom_url':
            if not url:
                return {
                    'status': 'offline',
                    'details': 'No URL provided for custom_url check',
                    'checked_at': datetime.now(timezone.utc).isoformat(),
                }
            return await self.check_url(url)
        else:
            return {
                'status': 'offline',
                'details': f"Unknown api_type: {api_type}",
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }
