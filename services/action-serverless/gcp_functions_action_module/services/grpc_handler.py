"""
gRPC Handler - Service implementation for GCP Functions Action gRPC.
"""
import asyncio
import logging
import json
import uuid
from concurrent import futures
from typing import Optional

import grpc

from config import Config
from services.gcp_functions_service import GCPFunctionsService

# Import generated proto files (will be generated during Docker build)
try:
    from grpc_proto import gcp_functions_action_pb2
    from grpc_proto import gcp_functions_action_pb2_grpc
except ImportError:
    # Placeholder for development
    logger = logging.getLogger(__name__)
    logger.warning("Proto files not generated yet - run protoc to generate")
    gcp_functions_action_pb2 = None
    gcp_functions_action_pb2_grpc = None


logger = logging.getLogger(__name__)


class GCPFunctionsActionServicer:
    """gRPC servicer for GCP Functions Action Service."""

    def __init__(self, gcp_functions_service: GCPFunctionsService):
        """Initialize servicer with GCP Functions service."""
        self.gcp_service = gcp_functions_service

    async def InvokeFunction(self, request, context):
        """
        Invoke a Cloud Function.

        Args:
            request: InvokeFunctionRequest
            context: gRPC context

        Returns:
            InvokeFunctionResponse
        """
        try:
            logger.info(
                f"InvokeFunction gRPC request: {request.function_name} "
                f"in {request.project}/{request.region}"
            )

            # Parse payload
            payload = json.loads(request.payload) if request.payload else {}

            # Convert headers map to dict
            headers = dict(request.headers) if request.headers else None

            # Invoke function
            result = await self.gcp_service.invoke_function(
                request.project,
                request.region,
                request.function_name,
                payload,
                headers
            )

            # Create response
            execution_id = str(uuid.uuid4())

            response = gcp_functions_action_pb2.InvokeFunctionResponse(
                success=result.get("success", False),
                status_code=result.get("status_code", 500),
                response=result.get("response", ""),
                error=result.get("error", ""),
                execution_id=execution_id,
                execution_time_ms=result.get("execution_time_ms", 0)
            )

            logger.info(
                f"InvokeFunction completed: {request.function_name} "
                f"(success={result.get('success')})"
            )

            return response

        except Exception as e:
            logger.error(f"InvokeFunction error: {e}", exc_info=True)

            return gcp_functions_action_pb2.InvokeFunctionResponse(
                success=False,
                status_code=500,
                error=str(e),
                execution_id="",
                execution_time_ms=0
            )

    async def InvokeHTTPFunction(self, request, context):
        """
        Invoke an HTTP-triggered function.

        Args:
            request: InvokeHTTPRequest
            context: gRPC context

        Returns:
            InvokeHTTPResponse
        """
        try:
            logger.info(
                f"InvokeHTTPFunction gRPC request: {request.method} {request.url}"
            )

            # Parse payload
            payload = json.loads(request.payload) if request.payload else None

            # Convert headers map to dict
            headers = dict(request.headers) if request.headers else None

            # Invoke HTTP function
            result = await self.gcp_service.invoke_http_function(
                request.url,
                payload,
                request.method or "POST",
                headers,
                request.timeout if request.timeout > 0 else None
            )

            # Create response
            response = gcp_functions_action_pb2.InvokeHTTPResponse(
                success=result.get("success", False),
                status_code=result.get("status_code", 500),
                response=result.get("response", ""),
                error=result.get("error", ""),
                execution_time_ms=result.get("execution_time_ms", 0)
            )

            # Add response headers
            if "response_headers" in result:
                for key, value in result["response_headers"].items():
                    response.response_headers[key] = str(value)

            logger.info(
                f"InvokeHTTPFunction completed: {request.url} "
                f"(success={result.get('success')})"
            )

            return response

        except Exception as e:
            logger.error(f"InvokeHTTPFunction error: {e}", exc_info=True)

            return gcp_functions_action_pb2.InvokeHTTPResponse(
                success=False,
                status_code=500,
                error=str(e),
                execution_time_ms=0
            )

    async def BatchInvoke(self, request, context):
        """
        Batch invoke multiple Cloud Functions.

        Args:
            request: BatchInvokeRequest
            context: gRPC context

        Returns:
            BatchInvokeResponse
        """
        try:
            logger.info(f"BatchInvoke gRPC request: {len(request.invocations)} invocations")

            # Execute all invocations concurrently
            tasks = []
            for invocation in request.invocations:
                task = self.InvokeFunction(invocation, context)
                tasks.append(task)

            # Wait for all to complete
            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successes and failures
            success_count = 0
            failure_count = 0

            processed_responses = []
            for response in responses:
                if isinstance(response, Exception):
                    # Handle exception
                    failure_count += 1
                    processed_responses.append(
                        gcp_functions_action_pb2.InvokeFunctionResponse(
                            success=False,
                            status_code=500,
                            error=str(response)
                        )
                    )
                else:
                    if response.success:
                        success_count += 1
                    else:
                        failure_count += 1
                    processed_responses.append(response)

            # Create batch response
            batch_response = gcp_functions_action_pb2.BatchInvokeResponse(
                responses=processed_responses,
                total_count=len(request.invocations),
                success_count=success_count,
                failure_count=failure_count
            )

            logger.info(
                f"BatchInvoke completed: {success_count} succeeded, "
                f"{failure_count} failed"
            )

            return batch_response

        except Exception as e:
            logger.error(f"BatchInvoke error: {e}", exc_info=True)

            return gcp_functions_action_pb2.BatchInvokeResponse(
                total_count=len(request.invocations),
                success_count=0,
                failure_count=len(request.invocations)
            )

    async def ListFunctions(self, request, context):
        """
        List Cloud Functions.

        Args:
            request: ListFunctionsRequest
            context: gRPC context

        Returns:
            ListFunctionsResponse
        """
        try:
            logger.info(
                f"ListFunctions gRPC request: {request.project}/{request.region}"
            )

            # List functions
            functions = await self.gcp_service.list_functions(
                request.project,
                request.region
            )

            # Create function info messages
            function_infos = []
            for func in functions:
                function_info = gcp_functions_action_pb2.FunctionInfo(
                    name=func.get("name", ""),
                    status=func.get("state", ""),
                    runtime=func.get("runtime", ""),
                    entry_point=func.get("entry_point", ""),
                    url=func.get("url", ""),
                    description=func.get("description", ""),
                    service_account=func.get("service_account", "")
                )
                function_infos.append(function_info)

            response = gcp_functions_action_pb2.ListFunctionsResponse(
                functions=function_infos
            )

            logger.info(f"ListFunctions completed: {len(functions)} functions")

            return response

        except Exception as e:
            logger.error(f"ListFunctions error: {e}", exc_info=True)

            return gcp_functions_action_pb2.ListFunctionsResponse()

    async def GetFunctionDetails(self, request, context):
        """
        Get details of a specific Cloud Function.

        Args:
            request: GetFunctionDetailsRequest
            context: gRPC context

        Returns:
            GetFunctionDetailsResponse
        """
        try:
            logger.info(
                f"GetFunctionDetails gRPC request: {request.function_name} "
                f"in {request.project}/{request.region}"
            )

            # Get function details
            details = await self.gcp_service.get_function_details(
                request.project,
                request.region,
                request.function_name
            )

            if details:
                # Create function info
                function_info = gcp_functions_action_pb2.FunctionInfo(
                    name=details.get("name", ""),
                    status=details.get("state", ""),
                    runtime=details.get("runtime", ""),
                    entry_point=details.get("entry_point", ""),
                    url=details.get("url", ""),
                    description=details.get("description", ""),
                    timeout=details.get("timeout", 60),
                    memory_mb=details.get("memory_mb", 256),
                    service_account=details.get("service_account", "")
                )

                # Add environment variables
                if "environment_variables" in details:
                    for key, value in details["environment_variables"].items():
                        function_info.environment_variables[key] = value

                response = gcp_functions_action_pb2.GetFunctionDetailsResponse(
                    success=True,
                    function=function_info
                )

                logger.info(f"GetFunctionDetails completed: {request.function_name}")

                return response
            else:
                return gcp_functions_action_pb2.GetFunctionDetailsResponse(
                    success=False,
                    error="Function not found"
                )

        except Exception as e:
            logger.error(f"GetFunctionDetails error: {e}", exc_info=True)

            return gcp_functions_action_pb2.GetFunctionDetailsResponse(
                success=False,
                error=str(e)
            )


class GrpcServer:
    """gRPC server wrapper."""

    def __init__(self, servicer: GCPFunctionsActionServicer, port: int):
        """Initialize gRPC server."""
        self.servicer = servicer
        self.port = port
        self.server: Optional[grpc.aio.Server] = None

    async def start(self):
        """Start gRPC server."""
        try:
            self.server = grpc.aio.server(
                futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
            )

            gcp_functions_action_pb2_grpc.add_GCPFunctionsActionServiceServicer_to_server(
                self.servicer,
                self.server
            )

            self.server.add_insecure_port(f"[::]:{self.port}")
            await self.server.start()

            logger.info(f"gRPC server started on port {self.port}")

        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop gRPC server."""
        if self.server:
            logger.info("Stopping gRPC server...")
            await self.server.stop(grace=5)
            logger.info("gRPC server stopped")
