"""
gRPC Handler for Lambda Action Service

Implements gRPC servicer for Lambda invocations
"""

import logging

import grpc
import jwt
from grpc_proto import lambda_action_pb2, lambda_action_pb2_grpc

from config import Config
from services.lambda_service import LambdaService

logger = logging.getLogger(__name__)


class LambdaActionServicer(lambda_action_pb2_grpc.LambdaActionServicer):
    """gRPC servicer for Lambda Action Service"""

    def __init__(self, lambda_service: LambdaService):
        """
        Initialize gRPC servicer

        Args:
            lambda_service: LambdaService instance
        """
        self.lambda_service = lambda_service
        logger.info("Lambda Action gRPC servicer initialized")

    def _verify_token(self, token: str) -> tuple[bool, str]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Tuple of (valid, error_message)
        """
        if not token:
            return False, "Missing authentication token"

        try:
            jwt.decode(
                token,
                Config.MODULE_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM]
            )
            return True, ""
        except jwt.ExpiredSignatureError:
            return False, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, f"Invalid token: {str(e)}"

    async def InvokeFunction(
        self,
        request: lambda_action_pb2.InvokeFunctionRequest,
        context: grpc.aio.ServicerContext
    ) -> lambda_action_pb2.InvokeFunctionResponse:
        """
        Invoke Lambda function

        Args:
            request: InvokeFunctionRequest
            context: gRPC context

        Returns:
            InvokeFunctionResponse
        """
        try:
            # Verify token
            valid, error = self._verify_token(request.token)
            if not valid:
                logger.warning(f"Authentication failed: {error}")
                return lambda_action_pb2.InvokeFunctionResponse(
                    success=False,
                    error=error
                )

            # Invoke function
            success, status_code, payload, func_error, log_result, exec_version = \
                await self.lambda_service.invoke_function(
                    request.function_name,
                    request.payload,
                    request.invocation_type or 'RequestResponse',
                    request.alias if request.alias else None,
                    request.version if request.version else None
                )

            return lambda_action_pb2.InvokeFunctionResponse(
                success=success,
                status_code=status_code,
                payload=payload,
                function_error=func_error,
                log_result=log_result,
                executed_version=exec_version,
                error='' if success else func_error
            )

        except Exception as e:
            error_msg = f"InvokeFunction error: {str(e)}"
            logger.error(error_msg)
            return lambda_action_pb2.InvokeFunctionResponse(
                success=False,
                error=error_msg
            )

    async def InvokeAsync(
        self,
        request: lambda_action_pb2.InvokeAsyncRequest,
        context: grpc.aio.ServicerContext
    ) -> lambda_action_pb2.InvokeAsyncResponse:
        """
        Invoke Lambda function asynchronously

        Args:
            request: InvokeAsyncRequest
            context: gRPC context

        Returns:
            InvokeAsyncResponse
        """
        try:
            # Verify token
            valid, error = self._verify_token(request.token)
            if not valid:
                logger.warning(f"Authentication failed: {error}")
                return lambda_action_pb2.InvokeAsyncResponse(
                    success=False,
                    error=error
                )

            # Invoke async
            success, status_code, request_id = await self.lambda_service.invoke_async(
                request.function_name,
                request.payload
            )

            return lambda_action_pb2.InvokeAsyncResponse(
                success=success,
                status_code=status_code,
                request_id=request_id,
                error='' if success else request_id  # request_id contains error on failure
            )

        except Exception as e:
            error_msg = f"InvokeAsync error: {str(e)}"
            logger.error(error_msg)
            return lambda_action_pb2.InvokeAsyncResponse(
                success=False,
                error=error_msg
            )

    async def BatchInvoke(
        self,
        request: lambda_action_pb2.BatchInvokeRequest,
        context: grpc.aio.ServicerContext
    ) -> lambda_action_pb2.BatchInvokeResponse:
        """
        Batch invoke Lambda functions

        Args:
            request: BatchInvokeRequest
            context: gRPC context

        Returns:
            BatchInvokeResponse
        """
        try:
            # Verify token
            valid, error = self._verify_token(request.token)
            if not valid:
                logger.warning(f"Authentication failed: {error}")
                return lambda_action_pb2.BatchInvokeResponse(
                    responses=[]
                )

            responses = []

            # Invoke each function
            for invocation in request.invocations:
                success, status_code, payload, func_error, log_result, exec_version = \
                    await self.lambda_service.invoke_function(
                        invocation.function_name,
                        invocation.payload,
                        invocation.invocation_type or 'RequestResponse',
                        invocation.alias if invocation.alias else None,
                        invocation.version if invocation.version else None
                    )

                responses.append(lambda_action_pb2.InvokeFunctionResponse(
                    success=success,
                    status_code=status_code,
                    payload=payload,
                    function_error=func_error,
                    log_result=log_result,
                    executed_version=exec_version,
                    error='' if success else func_error
                ))

            return lambda_action_pb2.BatchInvokeResponse(
                responses=responses
            )

        except Exception as e:
            error_msg = f"BatchInvoke error: {str(e)}"
            logger.error(error_msg)
            return lambda_action_pb2.BatchInvokeResponse(
                responses=[]
            )

    async def ListFunctions(
        self,
        request: lambda_action_pb2.ListFunctionsRequest,
        context: grpc.aio.ServicerContext
    ) -> lambda_action_pb2.ListFunctionsResponse:
        """
        List Lambda functions

        Args:
            request: ListFunctionsRequest
            context: gRPC context

        Returns:
            ListFunctionsResponse
        """
        try:
            # Verify token
            valid, error = self._verify_token(request.token)
            if not valid:
                logger.warning(f"Authentication failed: {error}")
                return lambda_action_pb2.ListFunctionsResponse(
                    success=False,
                    error=error
                )

            # List functions
            success, functions, next_marker = await self.lambda_service.list_functions(
                request.max_items if request.max_items > 0 else 50,
                request.next_marker if request.next_marker else None
            )

            if not success:
                return lambda_action_pb2.ListFunctionsResponse(
                    success=False,
                    error=next_marker  # Error message in next_marker on failure
                )

            # Convert to protobuf format
            func_infos = []
            for func in functions:
                func_infos.append(lambda_action_pb2.FunctionInfo(
                    function_name=func['function_name'],
                    function_arn=func['function_arn'],
                    runtime=func['runtime'],
                    role=func['role'],
                    handler=func['handler'],
                    code_size=func['code_size'],
                    description=func['description'],
                    timeout=func['timeout'],
                    memory_size=func['memory_size'],
                    last_modified=func['last_modified'],
                    version=func['version']
                ))

            return lambda_action_pb2.ListFunctionsResponse(
                success=True,
                functions=func_infos,
                next_marker=next_marker,
                error=''
            )

        except Exception as e:
            error_msg = f"ListFunctions error: {str(e)}"
            logger.error(error_msg)
            return lambda_action_pb2.ListFunctionsResponse(
                success=False,
                error=error_msg
            )

    async def GetFunctionConfig(
        self,
        request: lambda_action_pb2.GetFunctionConfigRequest,
        context: grpc.aio.ServicerContext
    ) -> lambda_action_pb2.GetFunctionConfigResponse:
        """
        Get Lambda function configuration

        Args:
            request: GetFunctionConfigRequest
            context: gRPC context

        Returns:
            GetFunctionConfigResponse
        """
        try:
            # Verify token
            valid, error = self._verify_token(request.token)
            if not valid:
                logger.warning(f"Authentication failed: {error}")
                return lambda_action_pb2.GetFunctionConfigResponse(
                    success=False,
                    error=error
                )

            # Get function config
            success, config = await self.lambda_service.get_function_config(
                request.function_name
            )

            if not success or not config:
                return lambda_action_pb2.GetFunctionConfigResponse(
                    success=False,
                    error="Failed to retrieve function configuration"
                )

            # Convert to protobuf format
            func_info = lambda_action_pb2.FunctionInfo(
                function_name=config['function_name'],
                function_arn=config['function_arn'],
                runtime=config['runtime'],
                role=config['role'],
                handler=config['handler'],
                code_size=config['code_size'],
                description=config['description'],
                timeout=config['timeout'],
                memory_size=config['memory_size'],
                last_modified=config['last_modified'],
                version=config['version']
            )

            return lambda_action_pb2.GetFunctionConfigResponse(
                success=True,
                function_info=func_info,
                error=''
            )

        except Exception as e:
            error_msg = f"GetFunctionConfig error: {str(e)}"
            logger.error(error_msg)
            return lambda_action_pb2.GetFunctionConfigResponse(
                success=False,
                error=error_msg
            )
