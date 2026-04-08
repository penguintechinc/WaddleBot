# -*- coding: utf-8 -*-
"""Generated gRPC service code for browser_source

Note: This is a simplified implementation designed for async gRPC operations.
For production use, regenerate these files using:
    python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/browser_source.proto
"""

import grpc
from proto import browser_source_pb2


class BrowserSourceServiceStub:
    """Client stub for BrowserSourceService"""

    def __init__(self, channel):
        """Initialize with a gRPC channel.

        Args:
            channel: grpc.aio.Channel instance
        """
        self.SendCaption = channel.unary_unary(
            '/waddlebot.browser_source.BrowserSourceService/SendCaption',
            request_serializer=browser_source_pb2.SendCaptionRequest.SerializeToString,
            response_deserializer=browser_source_pb2.SuccessResponse.FromString,
        )
        self.SendOverlayEvent = channel.unary_unary(
            '/waddlebot.browser_source.BrowserSourceService/SendOverlayEvent',
            request_serializer=browser_source_pb2.SendOverlayEventRequest.SerializeToString,
            response_deserializer=browser_source_pb2.SuccessResponse.FromString,
        )


class BrowserSourceServiceServicer:
    """Base servicer class for BrowserSourceService

    This class defines the interface that subclasses must implement.
    """

    async def SendCaption(self, request, context):
        """Send caption to browser source.

        Args:
            request: SendCaptionRequest
            context: grpc.aio.ServicerContext

        Returns:
            SuccessResponse
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    async def SendOverlayEvent(self, request, context):
        """Send overlay event.

        Args:
            request: SendOverlayEventRequest
            context: grpc.aio.ServicerContext

        Returns:
            SuccessResponse
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_BrowserSourceServiceServicer_to_server(servicer, server):
    """Add BrowserSourceServiceServicer to the gRPC server.

    Args:
        servicer: BrowserSourceServiceServicer instance
        server: grpc.aio.Server instance
    """
    rpc_method_handlers = {
        'SendCaption': grpc.method_handlers_generic_handler(
            'SendCaption',
            grpc.unary_unary_rpc_method_handler(
                servicer.SendCaption,
                request_deserializer=lambda x: browser_source_pb2.SendCaptionRequest.FromString(x),
                response_serializer=lambda x: x.SerializeToString(),
            ),
        ),
        'SendOverlayEvent': grpc.method_handlers_generic_handler(
            'SendOverlayEvent',
            grpc.unary_unary_rpc_method_handler(
                servicer.SendOverlayEvent,
                request_deserializer=lambda x: browser_source_pb2.SendOverlayEventRequest.FromString(x),
                response_serializer=lambda x: x.SerializeToString(),
            ),
        ),
    }

    generic_handler = grpc.method_handlers_generic_handler(
        'waddlebot.browser_source.BrowserSourceService',
        rpc_method_handlers,
    )
    server.add_generic_rpc_handlers((generic_handler,))
