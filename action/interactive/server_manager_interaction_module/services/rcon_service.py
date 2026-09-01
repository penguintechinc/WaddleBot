"""Source RCON protocol service for game server management."""
import logging
import time
from typing import Optional

from rcon.source import Client as RconClient

logger = logging.getLogger(__name__)


class RconService:
    """Manages RCON connections and command execution."""

    def __init__(self, config, encryption_service):
        self.config = config
        self.encryption = encryption_service
        self._pool = {}  # (host, port) -> (client, expires_at)
        self.ttl = config.RCON_CONNECTION_TTL

    def _get_connection(self, host: str, port: int, password: str) -> RconClient:
        key = (host, port)
        now = time.time()
        if key in self._pool:
            client, expires = self._pool[key]
            if now < expires:
                return client
            try:
                client.close()
            except Exception:
                pass
            del self._pool[key]

        client = RconClient(host, port, passwd=password)
        client.connect(True)
        self._pool[key] = (client, now + self.ttl)
        return client

    def _close_connection(self, host: str, port: int):
        key = (host, port)
        if key in self._pool:
            try:
                self._pool[key][0].close()
            except Exception:
                pass
            del self._pool[key]

    async def execute(self, host: str, port: int, password: str, command: str) -> dict:
        try:
            client = self._get_connection(host, port, password)
            response = client.run(command)
            return {'success': True, 'response': response}
        except Exception as exc:
            self._close_connection(host, port)
            logger.error("RCON execute failed %s:%s: %s", host, port, exc)
            return {'success': False, 'error': str(exc)}

    async def get_status(self, host: str, port: int, password: str) -> dict:
        result = await self.execute(host, port, password, 'status')
        if not result['success']:
            return {'online': False, 'error': result['error']}
        return {'online': True, 'raw': result['response']}

    async def get_players(self, host: str, port: int, password: str) -> dict:
        result = await self.execute(host, port, password, 'status')
        if not result['success']:
            return {'success': False, 'error': result['error']}
        return {'success': True, 'raw': result['response']}

    async def kick_player(self, host: str, port: int, password: str, player: str, reason: str = '') -> dict:
        cmd = f'kick {player}' + (f' "{reason}"' if reason else '')
        return await self.execute(host, port, password, cmd)

    async def ban_player(self, host: str, port: int, password: str, player: str, reason: str = '', duration: int = 0) -> dict:
        cmd = f'ban {player}' + (f' {duration}' if duration else '') + (f' "{reason}"' if reason else '')
        return await self.execute(host, port, password, cmd)

    async def test_connection(self, host: str, port: int, password: str) -> dict:
        try:
            client = RconClient(host, port, passwd=password)
            client.connect(True)
            response = client.run('status')
            client.close()
            return {'success': True, 'message': 'Connection successful', 'response': response[:200]}
        except Exception as exc:
            return {'success': False, 'error': str(exc)}
