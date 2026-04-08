"""
Webhook Executor Service

Executes outbound webhook actions in workflows with support for:
- Multiple HTTP methods (POST, GET, PUT, DELETE)
- HMAC signature generation for security
- Request body templating with expression substitution
- Response parsing and variable extraction
- Timeout and retry handling
- Custom headers
- Async execution with httpx
"""

import asyncio
import hashlib
import hmac
import json
import logging
import re
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx

logger = logging.getLogger(__name__)


class WebhookExecutionError(Exception):
    """Base exception for webhook execution errors."""

    pass


class WebhookTimeoutError(WebhookExecutionError):
    """Raised when webhook request times out."""

    pass


class WebhookRetryableError(WebhookExecutionError):
    """Raised when webhook request fails but is retryable."""

    pass


class WebhookNonRetryableError(WebhookExecutionError):
    """Raised when webhook request fails and should not be retried."""

    pass


class HMACSignatureGenerator:
    """Generates HMAC signatures for webhook authentication."""

    def __init__(self, secret: str, algorithm: str = "sha256"):
        """
        Initialize HMAC signature generator.

        Args:
            secret: Secret key for HMAC generation
            algorithm: HMAC algorithm (sha256, sha512, sha1)
        """
        self.secret = secret.encode() if isinstance(secret, str) else secret
        self.algorithm = algorithm.lower()

        if self.algorithm not in ["sha256", "sha512", "sha1"]:
            raise ValueError(f"Unsupported HMAC algorithm: {self.algorithm}")

    def generate(self, payload: str) -> str:
        """
        Generate HMAC signature for payload.

        Args:
            payload: Data to sign

        Returns:
            Hex-encoded HMAC signature
        """
        payload_bytes = payload.encode() if isinstance(payload, str) else payload
        signature = hmac.new(
            self.secret, payload_bytes, getattr(hashlib, self.algorithm)
        )
        return signature.hexdigest()

    def verify(self, payload: str, signature: str) -> bool:
        """
        Verify HMAC signature.

        Args:
            payload: Original data
            signature: Signature to verify

        Returns:
            True if signature is valid
        """
        expected_signature = self.generate(payload)
        return hmac.compare_digest(expected_signature, signature)


class ExpressionTemplater:
    """Handles expression substitution in webhook payloads."""

    EXPRESSION_PATTERN = re.compile(r"\$\{([^}]+)\}")
    BRACKET_PATTERN = re.compile(r"\$\(([^)]+)\)")

    @staticmethod
    def substitute(template: str, context: Dict[str, Any]) -> str:
        """
        Substitute expressions in template using context variables.

        Supports two formats:
        - ${variable_name} - Simple variable substitution
        - $(expression) - JavaScript-like expression evaluation

        Args:
            template: Template string with expressions
            context: Context dictionary with variables

        Returns:
            Template with substitutions applied
        """
        result = template

        # Handle ${variable} format
        def replace_variable(match):
            var_name = match.group(1)
            keys = var_name.split(".")

            value = context
            for key in keys:
                if isinstance(value, dict):
                    value = value.get(key)
                else:
                    return match.group(0)  # Return original if path invalid

            if value is None:
                return ""
            return str(value)

        result = ExpressionTemplater.EXPRESSION_PATTERN.sub(replace_variable, result)

        # Handle $(expression) format (simple evaluation)
        def evaluate_expression(match):
            expr = match.group(1)
            try:
                # Only allow safe evaluations (no import, exec, eval of dangerous code)
                # Support basic operations: comparisons, arithmetic, string concat
                return str(eval(expr, {"__builtins__": {}}, context))
            except Exception as e:
                logger.warning(f"Failed to evaluate expression '{expr}': {e}")
                return match.group(0)  # Return original if evaluation fails

        result = ExpressionTemplater.BRACKET_PATTERN.sub(evaluate_expression, result)

        return result

    @staticmethod
    def substitute_json(data: Any, context: Dict[str, Any]) -> Any:
        """
        Recursively substitute expressions in JSON data structure.

        Args:
            data: JSON-serializable data (dict, list, str, etc.)
            context: Context dictionary with variables

        Returns:
            Data with substitutions applied
        """
        if isinstance(data, dict):
            return {k: ExpressionTemplater.substitute_json(v, context) for k, v in data.items()}
        elif isinstance(data, list):
            return [ExpressionTemplater.substitute_json(item, context) for item in data]
        elif isinstance(data, str):
            return ExpressionTemplater.substitute(data, context)
        else:
            return data


class ResponseExtractor:
    """Extracts and parses webhook responses."""

    @staticmethod
    def extract_json(response: httpx.Response) -> Dict[str, Any]:
        """
        Extract JSON from response.

        Args:
            response: httpx.Response object

        Returns:
            Parsed JSON or error dict

        Raises:
            WebhookExecutionError: If response is not valid JSON
        """
        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise WebhookExecutionError(f"Invalid JSON in webhook response: {e}")

    @staticmethod
    def extract_variables(
        response: httpx.Response, extractors: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Extract variables from webhook response using JSON pointers/paths.

        Supports formats like:
        - "status" - Simple key access
        - "data.user.id" - Nested key access
        - "items[0].name" - Array access

        Args:
            response: httpx.Response object
            extractors: Dict mapping variable name to JSON path

        Returns:
            Dictionary of extracted variables
        """
        if not extractors:
            return {}

        extracted = {}

        try:
            if response.headers.get("content-type", "").startswith("application/json"):
                data = response.json()
            else:
                data = None
        except json.JSONDecodeError:
            data = None

        for var_name, path in extractors.items():
            try:
                value = ResponseExtractor._get_nested_value(data, path)
                extracted[var_name] = value
            except (KeyError, IndexError, TypeError, AttributeError) as e:
                logger.warning(f"Failed to extract variable '{var_name}' from path '{path}': {e}")
                extracted[var_name] = None

        return extracted

    @staticmethod
    def _get_nested_value(data: Any, path: str) -> Any:
        """
        Get nested value from data using path notation.

        Args:
            data: Data to traverse
            path: Path like "a.b.c" or "a[0].b"

        Returns:
            Value at path

        Raises:
            KeyError, IndexError, TypeError if path is invalid
        """
        if data is None:
            raise TypeError("Cannot traverse None")

        # Parse path segments
        segments = []
        current_segment = ""

        for char in path:
            if char == ".":
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
            elif char == "[":
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
            elif char == "]":
                if current_segment:
                    segments.append(f"[{current_segment}]")
                    current_segment = ""
            else:
                current_segment += char

        if current_segment:
            segments.append(current_segment)

        # Traverse data
        current = data
        for segment in segments:
            if segment.startswith("[") and segment.endswith("]"):
                index = int(segment[1:-1])
                current = current[index]
            else:
                current = current[segment]

        return current


class RetryPolicy:
    """Handles retry logic for webhook requests."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_status_codes: Optional[List[int]] = None,
    ):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum number of retries
            initial_delay: Initial retry delay in seconds
            max_delay: Maximum retry delay in seconds
            exponential_base: Base for exponential backoff
            retryable_status_codes: HTTP status codes to retry on
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.retryable_status_codes = retryable_status_codes or [408, 429, 500, 502, 503, 504]

    def is_retryable(self, error: Exception, status_code: Optional[int] = None) -> bool:
        """
        Determine if request should be retried.

        Args:
            error: Exception from request
            status_code: HTTP status code (if available)

        Returns:
            True if request should be retried
        """
        if isinstance(error, (WebhookTimeoutError, WebhookRetryableError)):
            return True

        if status_code and status_code in self.retryable_status_codes:
            return True

        if isinstance(error, httpx.RequestError):
            # Retry connection errors
            return True

        return False

    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for retry attempt using exponential backoff.

        Args:
            attempt: Attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


class WebhookExecutor:
    """Executes webhook actions with full feature support."""

    def __init__(
        self,
        timeout: float = 30.0,
        retry_policy: Optional[RetryPolicy] = None,
        verify_ssl: bool = True,
    ):
        """
        Initialize webhook executor.

        Args:
            timeout: Request timeout in seconds
            retry_policy: RetryPolicy instance
            verify_ssl: Whether to verify SSL certificates
        """
        self.timeout = timeout
        self.retry_policy = retry_policy or RetryPolicy()
        self.verify_ssl = verify_ssl

    async def execute(
        self,
        url: str,
        method: str = "POST",
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, Any]] = None,
        hmac_secret: Optional[str] = None,
        hmac_header: str = "X-Webhook-Signature",
        hmac_algorithm: str = "sha256",
        extractors: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute webhook request with full feature support.

        Args:
            url: Webhook URL to call
            method: HTTP method (POST, GET, PUT, DELETE)
            body: Request body (will be JSON-encoded)
            headers: Custom headers
            context: Context variables for expression substitution
            hmac_secret: Secret for HMAC signature generation
            hmac_header: Header name for HMAC signature
            hmac_algorithm: HMAC algorithm (sha256, sha512, sha1)
            extractors: Variable extractors from response

        Returns:
            Dict with keys:
            - success: bool
            - status_code: int
            - response_body: str or dict
            - extracted_variables: dict
            - error: str (if failed)
            - execution_time: float

        Raises:
            WebhookExecutionError: If execution fails permanently
        """
        start_time = time.time()
        context = context or {}
        headers = headers or {}
        method = method.upper()

        # Validate method
        if method not in ["POST", "GET", "PUT", "DELETE"]:
            raise WebhookExecutionError(f"Unsupported HTTP method: {method}")

        # Prepare request body
        request_body = None
        request_body_str = None

        if body:
            # Substitute expressions in body
            substituted_body = ExpressionTemplater.substitute_json(body, context)
            request_body = substituted_body
            request_body_str = json.dumps(substituted_body, separators=(",", ":"))

        # Prepare headers
        final_headers = {"User-Agent": "WaddleBot/1.0"}.copy()
        final_headers.update(headers)

        if request_body_str:
            final_headers["Content-Type"] = "application/json"

        # Generate HMAC signature if secret provided
        if hmac_secret and request_body_str:
            sig_gen = HMACSignatureGenerator(hmac_secret, hmac_algorithm)
            signature = sig_gen.generate(request_body_str)
            final_headers[hmac_header] = signature

        # Execute with retry logic
        last_error = None
        last_response = None

        for attempt in range(self.retry_policy.max_retries + 1):
            try:
                async with httpx.AsyncClient(verify=self.verify_ssl) as client:
                    response = await client.request(
                        method,
                        url,
                        json=request_body if method in ["POST", "PUT"] else None,
                        content=request_body_str if method in ["POST", "PUT"] else None,
                        headers=final_headers,
                        timeout=self.timeout,
                    )

                    last_response = response

                    # Check for HTTP errors
                    if response.status_code >= 400:
                        error_msg = f"HTTP {response.status_code}: {response.text[:500]}"

                        if self.retry_policy.is_retryable(
                            WebhookRetryableError(error_msg), response.status_code
                        ):
                            if attempt < self.retry_policy.max_retries:
                                delay = self.retry_policy.get_delay(attempt)
                                logger.warning(
                                    f"Webhook request failed with {response.status_code}, "
                                    f"retrying in {delay}s (attempt {attempt + 1}/{self.retry_policy.max_retries + 1})"
                                )
                                await asyncio.sleep(delay)
                                continue
                            else:
                                raise WebhookRetryableError(error_msg)
                        else:
                            raise WebhookNonRetryableError(error_msg)

                    # Success
                    return self._build_response(
                        response, extractors, start_time, request_body_str
                    )

            except httpx.TimeoutException as e:
                last_error = WebhookTimeoutError(f"Request timeout after {self.timeout}s")

                if attempt < self.retry_policy.max_retries:
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(
                        f"Webhook request timed out, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self.retry_policy.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue

            except httpx.RequestError as e:
                last_error = e

                if self.retry_policy.is_retryable(e):
                    if attempt < self.retry_policy.max_retries:
                        delay = self.retry_policy.get_delay(attempt)
                        logger.warning(
                            f"Webhook request failed: {e}, retrying in {delay}s "
                            f"(attempt {attempt + 1}/{self.retry_policy.max_retries + 1})"
                        )
                        await asyncio.sleep(delay)
                        continue

            except (WebhookRetryableError, WebhookNonRetryableError) as e:
                last_error = e

                if isinstance(e, WebhookRetryableError) and attempt < self.retry_policy.max_retries:
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(
                        f"Webhook request failed: {e}, retrying in {delay}s "
                        f"(attempt {attempt + 1}/{self.retry_policy.max_retries + 1})"
                    )
                    await asyncio.sleep(delay)
                    continue

        # All retries exhausted
        execution_time = time.time() - start_time

        if last_response is not None:
            return {
                "success": False,
                "status_code": last_response.status_code,
                "response_body": last_response.text,
                "extracted_variables": {},
                "error": str(last_error),
                "execution_time": execution_time,
            }

        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "extracted_variables": {},
            "error": str(last_error),
            "execution_time": execution_time,
        }

    def _build_response(
        self,
        response: httpx.Response,
        extractors: Optional[Dict[str, str]],
        start_time: float,
        request_body_str: Optional[str],
    ) -> Dict[str, Any]:
        """Build successful response dictionary."""
        execution_time = time.time() - start_time

        # Parse response body
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            try:
                response_body = response.json()
            except json.JSONDecodeError:
                response_body = response.text
        else:
            response_body = response.text

        # Extract variables
        extracted_variables = ResponseExtractor.extract_variables(response, extractors)

        return {
            "success": True,
            "status_code": response.status_code,
            "response_body": response_body,
            "extracted_variables": extracted_variables,
            "error": None,
            "execution_time": execution_time,
        }


class WebhookActionNode:
    """Represents a webhook action node in a workflow."""

    def __init__(
        self,
        node_id: str,
        url: str,
        method: str = "POST",
        body: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        hmac_secret: Optional[str] = None,
        hmac_header: str = "X-Webhook-Signature",
        hmac_algorithm: str = "sha256",
        extractors: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
        retry_config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize webhook action node.

        Args:
            node_id: Unique node identifier
            url: Webhook URL
            method: HTTP method
            body: Request body template
            headers: Custom headers
            hmac_secret: HMAC secret for signing
            hmac_header: Header name for signature
            hmac_algorithm: HMAC algorithm
            extractors: Variable extractors
            timeout: Request timeout
            retry_config: Retry configuration dict
        """
        self.node_id = node_id
        self.url = url
        self.method = method
        self.body = body
        self.headers = headers
        self.hmac_secret = hmac_secret
        self.hmac_header = hmac_header
        self.hmac_algorithm = hmac_algorithm
        self.extractors = extractors
        self.timeout = timeout

        # Initialize retry policy from config
        retry_config = retry_config or {}
        self.retry_policy = RetryPolicy(
            max_retries=retry_config.get("max_retries", 3),
            initial_delay=retry_config.get("initial_delay", 1.0),
            max_delay=retry_config.get("max_delay", 60.0),
            exponential_base=retry_config.get("exponential_base", 2.0),
        )

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute webhook action.

        Args:
            context: Workflow execution context

        Returns:
            Execution result dict
        """
        executor = WebhookExecutor(timeout=self.timeout, retry_policy=self.retry_policy)

        try:
            result = await executor.execute(
                url=self.url,
                method=self.method,
                body=self.body,
                headers=self.headers,
                context=context,
                hmac_secret=self.hmac_secret,
                hmac_header=self.hmac_header,
                hmac_algorithm=self.hmac_algorithm,
                extractors=self.extractors,
            )

            return {
                "node_id": self.node_id,
                "type": "webhook",
                "success": result["success"],
                "status_code": result["status_code"],
                "response_body": result["response_body"],
                "extracted_variables": result["extracted_variables"],
                "error": result["error"],
                "execution_time": result["execution_time"],
            }

        except Exception as e:
            logger.error(f"Webhook execution failed for node {self.node_id}: {e}")
            return {
                "node_id": self.node_id,
                "type": "webhook",
                "success": False,
                "status_code": None,
                "response_body": None,
                "extracted_variables": {},
                "error": str(e),
                "execution_time": 0.0,
            }
