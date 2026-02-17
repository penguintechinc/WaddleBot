"""gRPC Client Manager for Waddles Router Module"""
import asyncio
import logging
import time
from typing import Dict, Optional, Any
import grpc
import jwt

from config import Config

logger = logging.getLogger(__name__)


class GrpcClientManager:
    """Manages gRPC connections to action and core modules."""

    def __init__(self):
        self._channels: Dict[str, grpc.aio.Channel] = {}
        self._stubs: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

        # Module host mapping
        self._module_hosts = {
            'discord_action': Config.DISCORD_GRPC_HOST,
            'slack_action': Config.SLACK_GRPC_HOST,
            'twitch_action': Config.TWITCH_GRPC_HOST,
            'youtube_action': Config.YOUTUBE_GRPC_HOST,
            'lambda_action': Config.LAMBDA_GRPC_HOST,
            'gcp_functions_action': Config.GCP_FUNCTIONS_GRPC_HOST,
            'openwhisk_action': Config.OPENWHISK_GRPC_HOST,
            'reputation': Config.REPUTATION_GRPC_HOST,
            'workflow': Config.WORKFLOW_GRPC_HOST,
            'browser_source': Config.BROWSER_SOURCE_GRPC_HOST,
            'identity': Config.IDENTITY_GRPC_HOST,
            'hub_internal': Config.HUB_GRPC_HOST,
            'translate': Config.TRANSLATE_GRPC_HOST,
        }

    def generate_token(self, payload: Optional[Dict] = None) -> str:
        """Generate a JWT token for service-to-service authentication."""
        token_payload = {
            'service': Config.MODULE_NAME,
            'iat': int(time.time()),
            'exp': int(time.time()) + 3600,  # 1 hour expiry
        }
        if payload:
            token_payload.update(payload)
        return jwt.encode(token_payload, Config.SECRET_KEY, algorithm='HS256')

    async def get_channel(self, module_name: str) -> grpc.aio.Channel:
        """Get or create a gRPC channel for the specified module."""
        async with self._lock:
            if module_name not in self._channels or self._channels[module_name]._channel.closed():
                host = self._module_hosts.get(module_name)
                if not host:
                    raise ValueError(f"Unknown module: {module_name}")

                options = [
                    ('grpc.keepalive_time_ms', Config.GRPC_KEEPALIVE_TIME_MS),
                    ('grpc.keepalive_timeout_ms', Config.GRPC_KEEPALIVE_TIMEOUT_MS),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                ]

                channel = grpc.aio.insecure_channel(host, options=options)
                self._channels[module_name] = channel
                logger.info(f"Created gRPC channel to {module_name} at {host}")

            return self._channels[module_name]

    async def call_with_retry(
        self,
        method,
        request,
        max_retries: int = None,
        timeout: float = 30.0
    ) -> Any:
        """Call a gRPC method with retry logic and exponential backoff."""
        max_retries = max_retries or Config.GRPC_MAX_RETRIES
        last_error = None

        for attempt in range(max_retries):
            try:
                response = await asyncio.wait_for(
                    method(request),
                    timeout=timeout
                )
                return response
            except grpc.aio.AioRpcError as e:
                last_error = e
                if e.code() in (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED):
                    wait_time = (2 ** attempt) * 0.5  # Exponential backoff
                    logger.warning(
                        f"gRPC call failed (attempt {attempt + 1}/{max_retries}): {e.code()}. "
                        f"Retrying in {wait_time}s"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError(f"gRPC call timed out after {timeout}s")
                wait_time = (2 ** attempt) * 0.5
                logger.warning(f"gRPC call timed out (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time}s")
                await asyncio.sleep(wait_time)

        logger.error(f"gRPC call failed after {max_retries} attempts")
        raise last_error

    async def check_health(self, module_name: str) -> bool:
        """Check if a module's gRPC server is healthy."""
        try:
            channel = await self.get_channel(module_name)
            # Use gRPC health checking protocol
            await asyncio.wait_for(
                channel.channel_ready(),
                timeout=5.0
            )
            return True
        except Exception as e:
            logger.warning(f"Health check failed for {module_name}: {e}")
            return False

    async def close_all(self):
        """Close all gRPC channels."""
        async with self._lock:
            for name, channel in self._channels.items():
                try:
                    await channel.close()
                    logger.info(f"Closed gRPC channel to {name}")
                except Exception as e:
                    logger.warning(f"Error closing channel to {name}: {e}")
            self._channels.clear()
            self._stubs.clear()


# Singleton instance
_grpc_manager: Optional[GrpcClientManager] = None


def get_grpc_manager() -> GrpcClientManager:
    """Get the singleton GrpcClientManager instance."""
    global _grpc_manager
    if _grpc_manager is None:
        _grpc_manager = GrpcClientManager()
    return _grpc_manager
