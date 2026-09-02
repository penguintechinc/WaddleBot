"""
gRPC Service Handler for YouTube Action Module
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Optional

import grpc

from proto import youtube_action_pb2, youtube_action_pb2_grpc

from services.youtube_service import YouTubeService
from services.grpc_auth_interceptor import AuthInterceptor
from services.grpc_tls import bind_secure_port, default_server_options
from config import Config


logger = logging.getLogger(__name__)


class YouTubeActionServicer:
    """gRPC servicer implementation for YouTube actions.

    Runs on the asyncio gRPC stack. YouTubeService wraps the synchronous
    googleapiclient, so every call is dispatched to a bounded thread pool
    rather than blocking the event loop.
    """

    def __init__(self, youtube_service: YouTubeService, executor: ThreadPoolExecutor):
        self.youtube_service = youtube_service
        self._executor = executor

    async def _call(self, handler: Callable[..., Any], **kwargs: Any) -> Any:
        """Run a blocking YouTubeService call off the event loop."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, partial(handler, **kwargs))

    async def SendLiveChatMessage(self, request, context: grpc.aio.ServicerContext):
        """Send message to live chat"""
        try:
            result = await self._call(
                self.youtube_service.send_live_chat_message,
                live_chat_id=request.live_chat_id,
                message=request.message,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC SendLiveChatMessage error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def DeleteLiveChatMessage(self, request, context: grpc.aio.ServicerContext):
        """Delete live chat message"""
        try:
            result = await self._call(
                self.youtube_service.delete_live_chat_message,
                message_id=request.message_id, channel_id=request.channel_id
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC DeleteLiveChatMessage error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def BanLiveChatUser(self, request, context: grpc.aio.ServicerContext):
        """Ban user from live chat"""
        try:
            duration = request.duration_seconds if request.duration_seconds > 0 else None

            result = await self._call(
                self.youtube_service.ban_live_chat_user,
                live_chat_id=request.live_chat_id,
                channel_id=request.channel_id,
                target_channel_id=request.target_channel_id,
                duration_seconds=duration,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC BanLiveChatUser error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def UnbanLiveChatUser(self, request, context: grpc.aio.ServicerContext):
        """Unban user from live chat"""
        try:
            result = await self._call(
                self.youtube_service.unban_live_chat_user,
                live_chat_id=request.live_chat_id,
                channel_id=request.channel_id,
                target_channel_id=request.target_channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC UnbanLiveChatUser error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def AddModerator(self, request, context: grpc.aio.ServicerContext):
        """Add moderator to live chat"""
        try:
            result = await self._call(
                self.youtube_service.add_moderator,
                live_chat_id=request.live_chat_id,
                channel_id=request.channel_id,
                target_channel_id=request.target_channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC AddModerator error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def RemoveModerator(self, request, context: grpc.aio.ServicerContext):
        """Remove moderator from live chat"""
        try:
            result = await self._call(
                self.youtube_service.remove_moderator,
                live_chat_id=request.live_chat_id,
                channel_id=request.channel_id,
                target_channel_id=request.target_channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC RemoveModerator error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def UpdateVideoTitle(self, request, context: grpc.aio.ServicerContext):
        """Update video title"""
        try:
            result = await self._call(
                self.youtube_service.update_video_title,
                video_id=request.video_id,
                title=request.title,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC UpdateVideoTitle error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def UpdateVideoDescription(self, request, context: grpc.aio.ServicerContext):
        """Update video description"""
        try:
            result = await self._call(
                self.youtube_service.update_video_description,
                video_id=request.video_id,
                description=request.description,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC UpdateVideoDescription error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def AddToPlaylist(self, request, context: grpc.aio.ServicerContext):
        """Add video to playlist"""
        try:
            result = await self._call(
                self.youtube_service.add_to_playlist,
                playlist_id=request.playlist_id,
                video_id=request.video_id,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC AddToPlaylist error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def RemoveFromPlaylist(self, request, context: grpc.aio.ServicerContext):
        """Remove video from playlist"""
        try:
            result = await self._call(
                self.youtube_service.remove_from_playlist,
                playlist_item_id=request.playlist_item_id,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC RemoveFromPlaylist error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def CreatePlaylist(self, request, context: grpc.aio.ServicerContext):
        """Create new playlist"""
        try:
            result = await self._call(
                self.youtube_service.create_playlist,
                title=request.title,
                description=request.description,
                privacy=request.privacy,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.CreatePlaylistResponse(
                success=result["success"],
                message=result["message"],
                playlist_id=result.get("playlist_id", ""),
            )

        except Exception as e:
            logger.error(f"gRPC CreatePlaylist error: {e}")
            return youtube_action_pb2.CreatePlaylistResponse(
                success=False, message=str(e), playlist_id=""
            )

    async def UpdateBroadcastStatus(self, request, context: grpc.aio.ServicerContext):
        """Update broadcast status"""
        try:
            result = await self._call(
                self.youtube_service.update_broadcast_status,
                broadcast_id=request.broadcast_id,
                status=request.status,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC UpdateBroadcastStatus error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def InsertCuepoint(self, request, context: grpc.aio.ServicerContext):
        """Insert ad break cuepoint"""
        try:
            result = await self._call(
                self.youtube_service.insert_cuepoint,
                broadcast_id=request.broadcast_id,
                duration_seconds=request.duration_seconds,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC InsertCuepoint error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def PostComment(self, request, context: grpc.aio.ServicerContext):
        """Post comment on video"""
        try:
            result = await self._call(
                self.youtube_service.post_comment,
                video_id=request.video_id,
                text=request.text,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC PostComment error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def ReplyToComment(self, request, context: grpc.aio.ServicerContext):
        """Reply to comment"""
        try:
            result = await self._call(
                self.youtube_service.reply_to_comment,
                parent_id=request.parent_id,
                text=request.text,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC ReplyToComment error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def DeleteComment(self, request, context: grpc.aio.ServicerContext):
        """Delete comment"""
        try:
            result = await self._call(
                self.youtube_service.delete_comment,
                comment_id=request.comment_id, channel_id=request.channel_id
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC DeleteComment error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )

    async def SetCommentModeration(self, request, context: grpc.aio.ServicerContext):
        """Set comment moderation status"""
        try:
            result = await self._call(
                self.youtube_service.set_comment_moderation,
                comment_id=request.comment_id,
                status=request.status,
                channel_id=request.channel_id,
            )

            return youtube_action_pb2.ActionResponse(
                success=result["success"], message=result["message"]
            )

        except Exception as e:
            logger.error(f"gRPC SetCommentModeration error: {e}")
            return youtube_action_pb2.ActionResponse(
                success=False, message=str(e)
            )


class GRPCServer:
    """Manages the asyncio gRPC server and the thread pool its handlers use.

    The server itself is fully async; MAX_WORKERS bounds the pool that absorbs
    the synchronous YouTube Data API calls made inside each RPC.
    """

    def __init__(self, youtube_service: YouTubeService):
        self.youtube_service = youtube_service
        self.server: Optional[grpc.aio.Server] = None
        self._executor: Optional[ThreadPoolExecutor] = None

    async def start(self) -> None:
        """Bind and start the gRPC server on the running event loop."""
        self._executor = ThreadPoolExecutor(
            max_workers=Config.MAX_WORKERS, thread_name_prefix="youtube-api"
        )
        self.server = grpc.aio.server(
            interceptors=[AuthInterceptor()],
            options=default_server_options(),
        )

        servicer = YouTubeActionServicer(self.youtube_service, self._executor)
        youtube_action_pb2_grpc.add_YouTubeActionServicer_to_server(
            servicer, self.server
        )

        listen_addr = f"[::]:{Config.GRPC_PORT}"
        bind_secure_port(self.server, listen_addr)
        await self.server.start()

        logger.info(f"gRPC server started (TLS) on {listen_addr}")

    async def stop(self) -> None:
        """Stop the gRPC server, giving in-flight RPCs a grace period."""
        if self.server:
            await self.server.stop(grace=5)
            self.server = None
            logger.info("gRPC server stopped")
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    async def wait_for_termination(self) -> None:
        """Block until the server terminates."""
        if self.server:
            await self.server.wait_for_termination()
