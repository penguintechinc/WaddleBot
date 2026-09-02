import asyncio
import logging
from typing import Optional, Tuple

import grpc
from grpc import aio

from services.grpc_auth_interceptor import AuthInterceptor, require_auth

logger = logging.getLogger(__name__)


# Generated gRPC stubs would be imported here
# For now, we'll define a placeholder implementation
# In a real implementation, these would be generated from .proto files


class ActionServiceServicer:
    """gRPC servicer for action service."""

    def __init__(self, mattermost_service):
        """Initialize servicer with Mattermost service.

        Args:
            mattermost_service: Instance of MattermostService
        """
        self.service = mattermost_service

    async def SendMessage(self, request, context):
        """gRPC endpoint to send a message.

        Args:
            request: SendMessageRequest with channel_id, message, etc.
            context: gRPC context

        Returns:
            SendMessageResponse
        """
        await require_auth(context)

        try:
            result = await self.service.send_message(
                channel_id=request.channel_id,
                message=request.message,
                attachments=request.attachments if request.attachments else None,
            )

            return {
                'success': result.get('success'),
                'message_id': result.get('message_id', ''),
                'channel_id': result.get('channel_id', ''),
                'error': result.get('error', ''),
            }

        except Exception as e:
            logger.exception("gRPC SendMessage error")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            raise

    async def SendEphemeral(self, request, context):
        """gRPC endpoint to send an ephemeral message.

        Args:
            request: SendEphemeralRequest
            context: gRPC context

        Returns:
            SendEphemeralResponse
        """
        await require_auth(context)

        try:
            result = await self.service.send_ephemeral(
                channel_id=request.channel_id,
                user_id=request.user_id,
                message=request.message,
                attachments=request.attachments if request.attachments else None,
            )

            return {
                'success': result.get('success'),
                'user_id': result.get('user_id', ''),
                'channel_id': result.get('channel_id', ''),
                'error': result.get('error', ''),
            }

        except Exception as e:
            logger.exception("gRPC SendEphemeral error")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            raise

    async def AddReaction(self, request, context):
        """gRPC endpoint to add a reaction to a message.

        Args:
            request: AddReactionRequest
            context: gRPC context

        Returns:
            AddReactionResponse
        """
        await require_auth(context)

        try:
            result = await self.service.add_reaction(
                message_id=request.message_id,
                emoji_name=request.emoji_name,
            )

            return {
                'success': result.get('success'),
                'message_id': result.get('message_id', ''),
                'emoji_name': result.get('emoji_name', ''),
                'error': result.get('error', ''),
            }

        except Exception as e:
            logger.exception("gRPC AddReaction error")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            raise

    async def RemoveReaction(self, request, context):
        """gRPC endpoint to remove a reaction from a message.

        Args:
            request: RemoveReactionRequest
            context: gRPC context

        Returns:
            RemoveReactionResponse
        """
        await require_auth(context)

        try:
            result = await self.service.remove_reaction(
                message_id=request.message_id,
                emoji_name=request.emoji_name,
            )

            return {
                'success': result.get('success'),
                'message_id': result.get('message_id', ''),
                'emoji_name': result.get('emoji_name', ''),
                'error': result.get('error', ''),
            }

        except Exception as e:
            logger.exception("gRPC RemoveReaction error")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            raise

    async def CreateChannel(self, request, context):
        """gRPC endpoint to create a channel.

        Args:
            request: CreateChannelRequest
            context: gRPC context

        Returns:
            CreateChannelResponse
        """
        await require_auth(context)

        try:
            result = await self.service.create_channel(
                channel_name=request.channel_name,
                display_name=request.display_name,
                is_private=request.is_private,
                purpose=request.purpose if request.purpose else None,
            )

            return {
                'success': result.get('success'),
                'channel_id': result.get('channel_id', ''),
                'channel_name': result.get('channel_name', ''),
                'error': result.get('error', ''),
            }

        except Exception as e:
            logger.exception("gRPC CreateChannel error")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            raise

    async def GetActionHistory(self, request, context):
        """gRPC endpoint to get action history.

        Args:
            request: GetActionHistoryRequest
            context: gRPC context

        Returns:
            GetActionHistoryResponse
        """
        await require_auth(context)

        try:
            result = await self.service.get_action_history(
                limit=request.limit,
                offset=request.offset,
                action_type=request.action_type if request.action_type else None,
            )

            return {
                'success': result.get('success'),
                'history': [
                    {
                        'id': h.get('id'),
                        'action_type': h.get('action_type', ''),
                        'channel_id': h.get('channel_id', ''),
                        'message_id': h.get('message_id', ''),
                        'user_id': h.get('user_id', ''),
                        'status': h.get('status', ''),
                        'created_at': h.get('created_at', ''),
                    }
                    for h in result.get('history', [])
                ],
                'total': result.get('total', 0),
                'error': result.get('error', ''),
            }

        except Exception as e:
            logger.exception("gRPC GetActionHistory error")
            context.set_details(str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            raise


async def create_grpc_server(
    grpc_port: int,
    service,
) -> Tuple[aio.Server, asyncio.Task]:
    """Create and start gRPC server.

    Args:
        grpc_port: Port to listen on
        service: MattermostService instance

    Returns:
        Tuple of (gRPC server, asyncio task)
    """
    try:
        # Create gRPC server
        server = aio.server(interceptors=[AuthInterceptor()])

        # Add servicer to server
        servicer = ActionServiceServicer(service)
        # In a real implementation, you would register the servicer:
        # action_pb2_grpc.add_ActionServiceServicer_to_server(servicer, server)

        # Add port
        server.add_insecure_port(f'0.0.0.0:{grpc_port}')

        # Start server in background task
        async def run_server():
            await server.start()
            logger.info(f"gRPC server started on port {grpc_port}")
            try:
                await server.wait_for_termination()
            except asyncio.CancelledError:
                logger.info("gRPC server shutting down")
                await server.stop(0)

        grpc_task = asyncio.create_task(run_server())

        return server, grpc_task

    except Exception as e:
        logger.exception("Error creating gRPC server")
        raise
