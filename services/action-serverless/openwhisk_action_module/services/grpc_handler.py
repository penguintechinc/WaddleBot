"""
gRPC handler for receiving action tasks from processor/router.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

import grpc
from concurrent import futures

# Import generated protobuf classes (will be generated from proto file)
# from proto import openwhisk_action_pb2, openwhisk_action_pb2_grpc

from services.openwhisk_service import OpenWhiskService

logger = logging.getLogger(__name__)


class OpenWhiskActionServicer:
    """gRPC servicer for OpenWhisk actions."""

    def __init__(self, openwhisk_service: OpenWhiskService):
        """Initialize gRPC servicer."""
        self.openwhisk_service = openwhisk_service

    async def InvokeAction(self, request, context):
        """
        Invoke single OpenWhisk action.

        Args:
            request: InvokeActionRequest proto message
            context: gRPC context

        Returns:
            InvokeActionResponse proto message
        """
        namespace = request.namespace
        action_name = request.action_name
        blocking = request.blocking
        timeout = request.timeout if request.timeout > 0 else None

        # Parse payload JSON
        try:
            payload = json.loads(request.payload) if request.payload else {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {request.payload}")
            return {
                "success": False,
                "activation_id": "",
                "result": "",
                "duration": 0,
                "start_time": 0,
                "end_time": 0,
                "status": "",
                "error": "Invalid JSON payload"
            }

        logger.info(
            f"Invoking action: namespace={namespace}, action={action_name}, "
            f"blocking={blocking}, timeout={timeout}"
        )

        try:
            result = await self.openwhisk_service.invoke_action(
                namespace,
                action_name,
                payload,
                blocking,
                timeout
            )

            response = {
                "success": result.get("success", False),
                "activation_id": result.get("activation_id", ""),
                "result": json.dumps(result.get("result", {})),
                "duration": int(result.get("duration", 0)),
                "start_time": int(result.get("start_time", 0)),
                "end_time": int(result.get("end_time", 0)),
                "status": result.get("status", ""),
                "error": result.get("error", "")
            }

            logger.info(
                f"Action invocation complete: {namespace}/{action_name}, "
                f"success={response['success']}"
            )
            return response

        except Exception as e:
            logger.error(
                f"Action invocation failed: {namespace}/{action_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "activation_id": "",
                "result": "",
                "duration": 0,
                "start_time": 0,
                "end_time": 0,
                "status": "",
                "error": str(e)
            }

    async def InvokeActionAsync(self, request, context):
        """
        Invoke OpenWhisk action asynchronously.

        Args:
            request: InvokeActionAsyncRequest proto message
            context: gRPC context

        Returns:
            InvokeActionAsyncResponse proto message
        """
        namespace = request.namespace
        action_name = request.action_name

        # Parse payload JSON
        try:
            payload = json.loads(request.payload) if request.payload else {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {request.payload}")
            return {
                "success": False,
                "activation_id": "",
                "error": "Invalid JSON payload"
            }

        logger.info(
            f"Invoking action async: namespace={namespace}, action={action_name}"
        )

        try:
            result = await self.openwhisk_service.invoke_action_async(
                namespace,
                action_name,
                payload
            )

            response = {
                "success": result.get("success", False),
                "activation_id": result.get("activation_id", ""),
                "error": result.get("error", "")
            }

            logger.info(
                f"Async action invocation started: {namespace}/{action_name}, "
                f"activation_id={response['activation_id']}"
            )
            return response

        except Exception as e:
            logger.error(
                f"Async action invocation failed: {namespace}/{action_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "activation_id": "",
                "error": str(e)
            }

    async def InvokeSequence(self, request, context):
        """
        Invoke OpenWhisk sequence.

        Args:
            request: InvokeSequenceRequest proto message
            context: gRPC context

        Returns:
            InvokeSequenceResponse proto message
        """
        namespace = request.namespace
        sequence_name = request.sequence_name

        # Parse payload JSON
        try:
            payload = json.loads(request.payload) if request.payload else {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {request.payload}")
            return {
                "success": False,
                "activation_id": "",
                "result": "",
                "error": "Invalid JSON payload"
            }

        logger.info(
            f"Invoking sequence: namespace={namespace}, sequence={sequence_name}"
        )

        try:
            result = await self.openwhisk_service.invoke_sequence(
                namespace,
                sequence_name,
                payload
            )

            response = {
                "success": result.get("success", False),
                "activation_id": result.get("activation_id", ""),
                "result": json.dumps(result.get("result", {})),
                "error": result.get("error", "")
            }

            logger.info(
                f"Sequence invocation complete: {namespace}/{sequence_name}, "
                f"success={response['success']}"
            )
            return response

        except Exception as e:
            logger.error(
                f"Sequence invocation failed: {namespace}/{sequence_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "activation_id": "",
                "result": "",
                "error": str(e)
            }

    async def InvokeWebAction(self, request, context):
        """
        Invoke OpenWhisk web action.

        Args:
            request: InvokeWebActionRequest proto message
            context: gRPC context

        Returns:
            InvokeWebActionResponse proto message
        """
        namespace = request.namespace
        package_name = request.package_name
        action_name = request.action_name
        method = request.method or "POST"
        headers = dict(request.headers) if request.headers else {}

        # Parse payload JSON
        try:
            payload = json.loads(request.payload) if request.payload else {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {request.payload}")
            return {
                "success": False,
                "status_code": 400,
                "response": "",
                "response_headers": {},
                "error": "Invalid JSON payload"
            }

        logger.info(
            f"Invoking web action: namespace={namespace}, package={package_name}, "
            f"action={action_name}, method={method}"
        )

        try:
            result = await self.openwhisk_service.invoke_web_action(
                namespace,
                package_name,
                action_name,
                payload,
                method,
                headers
            )

            response = {
                "success": result.get("success", False),
                "status_code": result.get("status_code", 0),
                "response": json.dumps(result.get("response", {})),
                "response_headers": result.get("response_headers", {}),
                "error": result.get("error", "")
            }

            logger.info(
                f"Web action invocation complete: {namespace}/{package_name}/{action_name}, "
                f"success={response['success']}"
            )
            return response

        except Exception as e:
            logger.error(
                f"Web action invocation failed: {namespace}/{package_name}/{action_name}, "
                f"error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "status_code": 500,
                "response": "",
                "response_headers": {},
                "error": str(e)
            }

    async def FireTrigger(self, request, context):
        """
        Fire OpenWhisk trigger.

        Args:
            request: FireTriggerRequest proto message
            context: gRPC context

        Returns:
            FireTriggerResponse proto message
        """
        namespace = request.namespace
        trigger_name = request.trigger_name

        # Parse payload JSON
        try:
            payload = json.loads(request.payload) if request.payload else {}
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload: {request.payload}")
            return {
                "success": False,
                "activation_id": "",
                "error": "Invalid JSON payload"
            }

        logger.info(f"Firing trigger: namespace={namespace}, trigger={trigger_name}")

        try:
            result = await self.openwhisk_service.fire_trigger(
                namespace,
                trigger_name,
                payload
            )

            response = {
                "success": result.get("success", False),
                "activation_id": result.get("activation_id", ""),
                "error": result.get("error", "")
            }

            logger.info(
                f"Trigger fired: {namespace}/{trigger_name}, "
                f"success={response['success']}"
            )
            return response

        except Exception as e:
            logger.error(
                f"Trigger fire failed: {namespace}/{trigger_name}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "activation_id": "",
                "error": str(e)
            }

    async def GetActivation(self, request, context):
        """
        Get activation details.

        Args:
            request: GetActivationRequest proto message
            context: gRPC context

        Returns:
            GetActivationResponse proto message
        """
        namespace = request.namespace
        activation_id = request.activation_id

        logger.info(f"Getting activation: {activation_id}")

        try:
            result = await self.openwhisk_service.get_activation(
                namespace,
                activation_id
            )

            response = {
                "success": result.get("success", False),
                "activation_id": activation_id,
                "result": json.dumps(result.get("result", {})),
                "duration": int(result.get("duration", 0)),
                "status": result.get("status", ""),
                "logs": result.get("logs", []),
                "error": result.get("error", "")
            }

            logger.info(
                f"Activation retrieved: {activation_id}, "
                f"success={response['success']}"
            )
            return response

        except Exception as e:
            logger.error(
                f"Get activation failed: {activation_id}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "activation_id": activation_id,
                "result": "",
                "duration": 0,
                "status": "",
                "logs": [],
                "error": str(e)
            }

    async def ListActions(self, request, context):
        """
        List actions in namespace.

        Args:
            request: ListActionsRequest proto message
            context: gRPC context

        Returns:
            ListActionsResponse proto message
        """
        namespace = request.namespace
        limit = request.limit if request.limit > 0 else 30
        skip = request.skip if request.skip >= 0 else 0

        logger.info(f"Listing actions: namespace={namespace}, limit={limit}, skip={skip}")

        try:
            result = await self.openwhisk_service.list_actions(
                namespace,
                limit,
                skip
            )

            response = {
                "success": result.get("success", False),
                "actions": result.get("actions", []),
                "error": result.get("error", "")
            }

            logger.info(
                f"Actions listed: namespace={namespace}, count={len(response['actions'])}"
            )
            return response

        except Exception as e:
            logger.error(
                f"List actions failed: namespace={namespace}, error={e}",
                exc_info=True
            )
            return {
                "success": False,
                "actions": [],
                "error": str(e)
            }


class GrpcServer:
    """gRPC server wrapper."""

    def __init__(self, servicer: OpenWhiskActionServicer, port: int):
        """Initialize gRPC server."""
        self.servicer = servicer
        self.port = port
        self.server = None

    async def start(self):
        """Start gRPC server."""
        # Note: Actual gRPC server implementation would use generated protobuf code
        # This is a placeholder structure
        logger.info(f"Starting gRPC server on port {self.port}")

        # In production, would be:
        # self.server = grpc.aio.server()
        # openwhisk_action_pb2_grpc.add_OpenWhiskActionServiceServicer_to_server(
        #     self.servicer, self.server
        # )
        # self.server.add_insecure_port(f'[::]:{self.port}')
        # await self.server.start()

        logger.info(f"gRPC server started on port {self.port}")

    async def stop(self):
        """Stop gRPC server."""
        if self.server:
            logger.info("Stopping gRPC server")
            await self.server.stop(grace=5)
            logger.info("gRPC server stopped")
