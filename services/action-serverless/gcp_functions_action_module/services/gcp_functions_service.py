"""
GCP Functions Service - Cloud Functions invocation and management.
"""
import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime

import aiohttp
from google.cloud import functions_v2
from google.auth import default
from google.auth.transport.requests import Request
from google.oauth2 import service_account
import google.auth.transport.requests

from config import Config


logger = logging.getLogger(__name__)


class GCPFunctionsService:
    """Service for invoking and managing GCP Cloud Functions."""

    def __init__(self, credentials=None):
        """Initialize GCP Functions service."""
        self.project_id = Config.GCP_PROJECT_ID
        self.region = Config.GCP_REGION
        self.credentials = credentials or self._load_credentials()
        self.http_session: Optional[aiohttp.ClientSession] = None

    def _load_credentials(self):
        """Load GCP credentials from service account key."""
        try:
            # Try loading from JSON string or file path
            key_data = Config.GCP_SERVICE_ACCOUNT_KEY

            if not key_data:
                logger.warning("No GCP_SERVICE_ACCOUNT_KEY configured - running in degraded mode")
                return None

            if key_data.startswith('{'):
                # JSON string
                key_info = json.loads(key_data)
                credentials = service_account.Credentials.from_service_account_info(key_info)
            else:
                # File path
                credentials = service_account.Credentials.from_service_account_file(key_data)

            logger.info("GCP credentials loaded successfully")
            return credentials

        except Exception as e:
            logger.warning(f"Failed to load GCP credentials: {e}")
            # Fall back to default credentials (useful for GCE/GKE)
            try:
                credentials, project = default()
                logger.info("Using default GCP credentials")
                return credentials
            except Exception as e2:
                logger.warning(f"No GCP credentials available - running in degraded mode: {e2}")
                return None

    async def _ensure_session(self):
        """Ensure aiohttp session exists."""
        if self.http_session is None or self.http_session.closed:
            self.http_session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session."""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()

    def _get_id_token(self, target_audience: str) -> Optional[str]:
        """Get ID token for authenticating to Cloud Functions."""
        if not self.credentials:
            logger.warning("No credentials available for ID token generation")
            return None

        try:
            # Refresh credentials if needed
            if not self.credentials.valid:
                auth_req = google.auth.transport.requests.Request()
                self.credentials.refresh(auth_req)

            # Get ID token
            from google.oauth2 import id_token
            id_token_credentials = id_token.fetch_id_token(
                google.auth.transport.requests.Request(),
                target_audience
            )

            return id_token_credentials

        except Exception as e:
            logger.error(f"Failed to get ID token: {e}")
            raise

    async def invoke_function(
        self,
        project: str,
        region: str,
        function_name: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Invoke a Cloud Function with authentication.

        Args:
            project: GCP project ID
            region: GCP region (e.g., us-central1)
            function_name: Name of the Cloud Function
            payload: JSON payload to send
            headers: Optional additional headers

        Returns:
            Dict with success, status_code, response, error
        """
        start_time = time.time()

        try:
            await self._ensure_session()

            # Build function URL
            function_url = f"https://{region}-{project}.cloudfunctions.net/{function_name}"

            logger.info(f"Invoking Cloud Function: {function_url}")

            # Get ID token for authentication (if credentials available)
            id_token = self._get_id_token(function_url)

            # Prepare headers
            request_headers = {
                "Content-Type": "application/json",
            }
            if id_token:
                request_headers["Authorization"] = f"Bearer {id_token}"

            if headers:
                request_headers.update(headers)

            # Make HTTP POST request
            async with self.http_session.post(
                function_url,
                json=payload,
                headers=request_headers,
                timeout=aiohttp.ClientTimeout(total=Config.FUNCTION_TIMEOUT)
            ) as response:
                status_code = response.status
                response_text = await response.text()

                execution_time = int((time.time() - start_time) * 1000)

                if status_code >= 200 and status_code < 300:
                    logger.info(
                        f"Function invoked successfully: {function_name} "
                        f"(status={status_code}, time={execution_time}ms)"
                    )

                    return {
                        "success": True,
                        "status_code": status_code,
                        "response": response_text,
                        "execution_time_ms": execution_time
                    }
                else:
                    logger.error(
                        f"Function invocation failed: {function_name} "
                        f"(status={status_code})"
                    )

                    return {
                        "success": False,
                        "status_code": status_code,
                        "response": response_text,
                        "error": f"Function returned status code {status_code}",
                        "execution_time_ms": execution_time
                    }

        except asyncio.TimeoutError:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Function invocation timed out: {function_name}")

            return {
                "success": False,
                "status_code": 504,
                "error": "Function invocation timed out",
                "execution_time_ms": execution_time
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Function invocation error: {e}", exc_info=True)

            return {
                "success": False,
                "status_code": 500,
                "error": str(e),
                "execution_time_ms": execution_time
            }

    async def invoke_http_function(
        self,
        url: str,
        payload: Optional[Dict[str, Any]] = None,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Invoke an HTTP-triggered Cloud Function or any HTTP endpoint.

        Args:
            url: Full URL of the function
            payload: Optional JSON payload
            method: HTTP method (GET, POST, PUT, DELETE)
            headers: Optional headers
            timeout: Optional timeout in seconds

        Returns:
            Dict with success, status_code, response, response_headers, error
        """
        start_time = time.time()

        try:
            await self._ensure_session()

            logger.info(f"Invoking HTTP function: {method} {url}")

            # Prepare headers
            request_headers = {"Content-Type": "application/json"}
            if headers:
                request_headers.update(headers)

            # Prepare request kwargs
            kwargs = {
                "headers": request_headers,
                "timeout": aiohttp.ClientTimeout(total=timeout or Config.REQUEST_TIMEOUT)
            }

            if payload and method in ["POST", "PUT", "PATCH"]:
                kwargs["json"] = payload

            # Make HTTP request
            async with self.http_session.request(method, url, **kwargs) as response:
                status_code = response.status
                response_text = await response.text()
                response_headers = dict(response.headers)

                execution_time = int((time.time() - start_time) * 1000)

                if status_code >= 200 and status_code < 300:
                    logger.info(
                        f"HTTP function invoked successfully: {url} "
                        f"(status={status_code}, time={execution_time}ms)"
                    )

                    return {
                        "success": True,
                        "status_code": status_code,
                        "response": response_text,
                        "response_headers": response_headers,
                        "execution_time_ms": execution_time
                    }
                else:
                    logger.error(
                        f"HTTP function invocation failed: {url} "
                        f"(status={status_code})"
                    )

                    return {
                        "success": False,
                        "status_code": status_code,
                        "response": response_text,
                        "response_headers": response_headers,
                        "error": f"HTTP request returned status code {status_code}",
                        "execution_time_ms": execution_time
                    }

        except asyncio.TimeoutError:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"HTTP function invocation timed out: {url}")

            return {
                "success": False,
                "status_code": 504,
                "error": "HTTP request timed out",
                "execution_time_ms": execution_time
            }

        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"HTTP function invocation error: {e}", exc_info=True)

            return {
                "success": False,
                "status_code": 500,
                "error": str(e),
                "execution_time_ms": execution_time
            }

    async def invoke_with_auth(
        self,
        function_name: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convenience method to invoke function with default project/region.

        Args:
            function_name: Name of the Cloud Function
            payload: JSON payload

        Returns:
            Dict with invocation result
        """
        return await self.invoke_function(
            self.project_id,
            self.region,
            function_name,
            payload
        )

    async def list_functions(self, project: str, region: str) -> List[Dict[str, Any]]:
        """
        List Cloud Functions in a project/region.

        Args:
            project: GCP project ID
            region: GCP region

        Returns:
            List of function info dicts
        """
        try:
            # Initialize Cloud Functions client
            client = functions_v2.FunctionServiceClient(credentials=self.credentials)

            # Build parent path
            parent = f"projects/{project}/locations/{region}"

            logger.info(f"Listing functions in {parent}")

            # List functions
            functions = []
            request = functions_v2.ListFunctionsRequest(parent=parent)

            for function in client.list_functions(request=request):
                functions.append({
                    "name": function.name.split('/')[-1],
                    "full_name": function.name,
                    "state": str(function.state),
                    "runtime": function.build_config.runtime if function.build_config else "unknown",
                    "entry_point": function.build_config.entry_point if function.build_config else "unknown",
                    "url": function.service_config.uri if function.service_config else "",
                    "description": function.description,
                    "service_account": function.service_config.service_account_email if function.service_config else ""
                })

            logger.info(f"Found {len(functions)} functions")
            return functions

        except Exception as e:
            logger.error(f"Failed to list functions: {e}", exc_info=True)
            return []

    async def get_function_details(
        self,
        project: str,
        region: str,
        function_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific Cloud Function.

        Args:
            project: GCP project ID
            region: GCP region
            function_name: Name of the Cloud Function

        Returns:
            Dict with function details or None if not found
        """
        try:
            # Initialize Cloud Functions client
            client = functions_v2.FunctionServiceClient(credentials=self.credentials)

            # Build function path
            name = f"projects/{project}/locations/{region}/functions/{function_name}"

            logger.info(f"Getting function details: {name}")

            # Get function
            request = functions_v2.GetFunctionRequest(name=name)
            function = client.get_function(request=request)

            details = {
                "name": function.name.split('/')[-1],
                "full_name": function.name,
                "state": str(function.state),
                "runtime": function.build_config.runtime if function.build_config else "unknown",
                "entry_point": function.build_config.entry_point if function.build_config else "unknown",
                "url": function.service_config.uri if function.service_config else "",
                "description": function.description,
                "timeout": function.service_config.timeout_seconds if function.service_config else 60,
                "memory_mb": function.service_config.available_memory if function.service_config else 256,
                "environment_variables": dict(function.service_config.environment_variables) if function.service_config else {},
                "service_account": function.service_config.service_account_email if function.service_config else ""
            }

            logger.info(f"Retrieved function details: {function_name}")
            return details

        except Exception as e:
            logger.error(f"Failed to get function details: {e}", exc_info=True)
            return None
