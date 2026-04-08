"""
OpenWhisk invocation service using aiohttp for async HTTP calls.
Handles communication with OpenWhisk REST API.
"""
import asyncio
import base64
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import aiohttp
from aiohttp import ClientTimeout, TCPConnector

from config import Config

logger = logging.getLogger(__name__)


class OpenWhiskService:
    """Service for invoking OpenWhisk actions and managing triggers."""

    def __init__(self):
        """Initialize OpenWhisk service."""
        self.api_host = Config.OPENWHISK_API_HOST.rstrip('/')
        self.auth_key = Config.OPENWHISK_AUTH_KEY
        self.namespace = Config.OPENWHISK_NAMESPACE
        self.insecure = Config.OPENWHISK_INSECURE

        # Create auth header (Basic auth with namespace:key)
        auth_string = base64.b64encode(self.auth_key.encode()).decode()
        self.auth_header = f"Basic {auth_string}"

        # Session will be created on first use
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = ClientTimeout(total=Config.REQUEST_TIMEOUT)
            connector = TCPConnector(ssl=not self.insecure)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json"
                }
            )
        return self._session

    async def close(self):
        """Close aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def invoke_action(
        self,
        namespace: str,
        action_name: str,
        payload: Dict[str, Any],
        blocking: bool = True,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Invoke an OpenWhisk action.

        Args:
            namespace: OpenWhisk namespace
            action_name: Name of the action to invoke
            payload: Action parameters
            blocking: Wait for action to complete
            timeout: Action timeout in milliseconds

        Returns:
            Dictionary with action response
        """
        try:
            session = await self._get_session()

            url = f"{self.api_host}/api/v1/namespaces/{namespace}/actions/{action_name}"

            params = {"blocking": str(blocking).lower()}
            if timeout:
                timeout_ms = min(timeout, Config.MAX_ACTION_TIMEOUT)
                params["timeout"] = str(timeout_ms)

            logger.info(
                f"Invoking OpenWhisk action: {namespace}/{action_name}, "
                f"blocking={blocking}, timeout={timeout}"
            )

            start_time = datetime.utcnow()

            async with session.post(url, json=payload, params=params) as response:
                result = await response.json()

                duration = (datetime.utcnow() - start_time).total_seconds() * 1000

                if response.status >= 400:
                    logger.error(
                        f"Action invocation failed: {namespace}/{action_name}, "
                        f"status={response.status}, error={result}"
                    )
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                        "status_code": response.status
                    }

                logger.info(
                    f"Action invocation successful: {namespace}/{action_name}, "
                    f"duration={duration:.2f}ms"
                )

                # Extract relevant data from response
                return {
                    "success": True,
                    "activation_id": result.get("activationId", ""),
                    "result": result.get("response", {}).get("result", {}),
                    "duration": duration,
                    "start_time": result.get("start", 0),
                    "end_time": result.get("end", 0),
                    "status": result.get("response", {}).get("status", ""),
                }

        except asyncio.TimeoutError:
            logger.error(f"Action invocation timed out: {namespace}/{action_name}")
            return {
                "success": False,
                "error": "Request timed out",
                "timeout": timeout or Config.REQUEST_TIMEOUT
            }
        except Exception as e:
            logger.error(
                f"Action invocation failed: {namespace}/{action_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def invoke_action_async(
        self,
        namespace: str,
        action_name: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke an OpenWhisk action asynchronously (non-blocking).

        Args:
            namespace: OpenWhisk namespace
            action_name: Name of the action to invoke
            payload: Action parameters

        Returns:
            Dictionary with activation ID
        """
        result = await self.invoke_action(namespace, action_name, payload, blocking=False)
        return {
            "success": result.get("success", False),
            "activation_id": result.get("activation_id", "")
        }

    async def invoke_sequence(
        self,
        namespace: str,
        sequence_name: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Invoke an OpenWhisk sequence.

        Args:
            namespace: OpenWhisk namespace
            sequence_name: Name of the sequence to invoke
            payload: Sequence parameters

        Returns:
            Dictionary with sequence response
        """
        # Sequences are invoked the same way as actions
        return await self.invoke_action(namespace, sequence_name, payload, blocking=True)

    async def invoke_web_action(
        self,
        namespace: str,
        package_name: str,
        action_name: str,
        payload: Dict[str, Any],
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an OpenWhisk web action.

        Args:
            namespace: OpenWhisk namespace
            package_name: Package name (use 'default' for no package)
            action_name: Name of the action
            payload: Action parameters
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            headers: Additional HTTP headers

        Returns:
            Dictionary with web action response
        """
        try:
            session = await self._get_session()

            # Web actions have different URL format
            url = f"{self.api_host}/api/v1/web/{namespace}/{package_name}/{action_name}"

            request_headers = headers or {}

            logger.info(
                f"Invoking OpenWhisk web action: {namespace}/{package_name}/{action_name}, "
                f"method={method}"
            )

            async with session.request(
                method,
                url,
                json=payload if method in ["POST", "PUT", "PATCH"] else None,
                params=payload if method == "GET" else None,
                headers=request_headers
            ) as response:
                # Web actions can return any content type
                content_type = response.headers.get("Content-Type", "")

                if "application/json" in content_type:
                    result = await response.json()
                else:
                    result = {"response": await response.text()}

                logger.info(
                    f"Web action invocation complete: {namespace}/{package_name}/{action_name}, "
                    f"status={response.status}"
                )

                return {
                    "success": response.status < 400,
                    "status_code": response.status,
                    "response": result,
                    "response_headers": dict(response.headers)
                }

        except Exception as e:
            logger.error(
                f"Web action invocation failed: {namespace}/{package_name}/{action_name}, "
                f"error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def fire_trigger(
        self,
        namespace: str,
        trigger_name: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Fire an OpenWhisk trigger.

        Args:
            namespace: OpenWhisk namespace
            trigger_name: Name of the trigger
            payload: Trigger parameters

        Returns:
            Dictionary with trigger response
        """
        try:
            session = await self._get_session()

            url = f"{self.api_host}/api/v1/namespaces/{namespace}/triggers/{trigger_name}"

            logger.info(f"Firing OpenWhisk trigger: {namespace}/{trigger_name}")

            async with session.post(url, json=payload) as response:
                result = await response.json()

                if response.status >= 400:
                    logger.error(
                        f"Trigger fire failed: {namespace}/{trigger_name}, "
                        f"status={response.status}, error={result}"
                    )
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }

                logger.info(f"Trigger fired successfully: {namespace}/{trigger_name}")

                return {
                    "success": True,
                    "activation_id": result.get("activationId", "")
                }

        except Exception as e:
            logger.error(
                f"Trigger fire failed: {namespace}/{trigger_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e)
            }

    async def list_actions(
        self,
        namespace: str,
        limit: int = 30,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        List actions in a namespace.

        Args:
            namespace: OpenWhisk namespace
            limit: Maximum number of actions to return
            skip: Number of actions to skip

        Returns:
            Dictionary with list of actions
        """
        try:
            session = await self._get_session()

            url = f"{self.api_host}/api/v1/namespaces/{namespace}/actions"

            params = {
                "limit": min(limit, 200),
                "skip": skip
            }

            logger.info(f"Listing OpenWhisk actions: {namespace}")

            async with session.get(url, params=params) as response:
                result = await response.json()

                if response.status >= 400:
                    logger.error(
                        f"List actions failed: {namespace}, "
                        f"status={response.status}, error={result}"
                    )
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error"),
                        "actions": []
                    }

                actions = [
                    {
                        "name": action.get("name", ""),
                        "namespace": action.get("namespace", ""),
                        "version": action.get("version", ""),
                        "published": action.get("publish", False)
                    }
                    for action in result
                ]

                logger.info(f"Listed {len(actions)} actions in {namespace}")

                return {
                    "success": True,
                    "actions": actions
                }

        except Exception as e:
            logger.error(
                f"List actions failed: {namespace}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "actions": []
            }

    async def get_activation(
        self,
        namespace: str,
        activation_id: str
    ) -> Dict[str, Any]:
        """
        Get activation details.

        Args:
            namespace: OpenWhisk namespace
            activation_id: Activation ID

        Returns:
            Dictionary with activation details
        """
        try:
            session = await self._get_session()

            url = f"{self.api_host}/api/v1/namespaces/{namespace}/activations/{activation_id}"

            logger.info(f"Getting activation: {activation_id}")

            async with session.get(url) as response:
                result = await response.json()

                if response.status >= 400:
                    logger.error(
                        f"Get activation failed: {activation_id}, "
                        f"status={response.status}, error={result}"
                    )
                    return {
                        "success": False,
                        "error": result.get("error", "Unknown error")
                    }

                logger.info(f"Retrieved activation: {activation_id}")

                return {
                    "success": True,
                    "activation_id": activation_id,
                    "result": result.get("response", {}).get("result", {}),
                    "duration": result.get("duration", 0),
                    "status": result.get("response", {}).get("status", ""),
                    "logs": result.get("logs", [])
                }

        except Exception as e:
            logger.error(
                f"Get activation failed: {activation_id}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "error": str(e)
            }
