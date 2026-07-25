"""
gRPC Service Handler for YouTube Action Module
"""
import logging
import grpc
from concurrent import futures

from proto import youtube_action_pb2, youtube_action_pb2_grpc

from services.youtube_service import YouTubeService
from config import Config


logger = logging.getLogger(__name__)


class YouTubeActionServicer:
    """gRPC servicer implementation for YouTube actions"""

    def __init__(self, youtube_service: YouTubeService):
        self.youtube_service = youtube_service

    def SendLiveChatMessage(self, request, context):
        """Send message to live chat"""
        try:
            result = self.youtube_service.send_live_chat_message(
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

    def DeleteLiveChatMessage(self, request, context):
        """Delete live chat message"""
        try:
            result = self.youtube_service.delete_live_chat_message(
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

    def BanLiveChatUser(self, request, context):
        """Ban user from live chat"""
        try:
            duration = request.duration_seconds if request.duration_seconds > 0 else None

            result = self.youtube_service.ban_live_chat_user(
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

    def UnbanLiveChatUser(self, request, context):
        """Unban user from live chat"""
        try:
            result = self.youtube_service.unban_live_chat_user(
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

    def AddModerator(self, request, context):
        """Add moderator to live chat"""
        try:
            result = self.youtube_service.add_moderator(
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

    def RemoveModerator(self, request, context):
        """Remove moderator from live chat"""
        try:
            result = self.youtube_service.remove_moderator(
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

    def UpdateVideoTitle(self, request, context):
        """Update video title"""
        try:
            result = self.youtube_service.update_video_title(
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

    def UpdateVideoDescription(self, request, context):
        """Update video description"""
        try:
            result = self.youtube_service.update_video_description(
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

    def AddToPlaylist(self, request, context):
        """Add video to playlist"""
        try:
            result = self.youtube_service.add_to_playlist(
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

    def RemoveFromPlaylist(self, request, context):
        """Remove video from playlist"""
        try:
            result = self.youtube_service.remove_from_playlist(
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

    def CreatePlaylist(self, request, context):
        """Create new playlist"""
        try:
            result = self.youtube_service.create_playlist(
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

    def UpdateBroadcastStatus(self, request, context):
        """Update broadcast status"""
        try:
            result = self.youtube_service.update_broadcast_status(
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

    def InsertCuepoint(self, request, context):
        """Insert ad break cuepoint"""
        try:
            result = self.youtube_service.insert_cuepoint(
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

    def PostComment(self, request, context):
        """Post comment on video"""
        try:
            result = self.youtube_service.post_comment(
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

    def ReplyToComment(self, request, context):
        """Reply to comment"""
        try:
            result = self.youtube_service.reply_to_comment(
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

    def DeleteComment(self, request, context):
        """Delete comment"""
        try:
            result = self.youtube_service.delete_comment(
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

    def SetCommentModeration(self, request, context):
        """Set comment moderation status"""
        try:
            result = self.youtube_service.set_comment_moderation(
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
    """gRPC server manager"""

    def __init__(self, youtube_service: YouTubeService):
        self.youtube_service = youtube_service
        self.server = None

    def start(self) -> None:
        """Start gRPC server"""
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        )

        servicer = YouTubeActionServicer(self.youtube_service)
        youtube_action_pb2_grpc.add_YouTubeActionServicer_to_server(
            servicer, self.server
        )

        listen_addr = f"[::]:{Config.GRPC_PORT}"
        self.server.add_insecure_port(listen_addr)
        self.server.start()

        logger.info(f"gRPC server started on {listen_addr}")

    def stop(self) -> None:
        """Stop gRPC server"""
        if self.server:
            self.server.stop(grace=5)
            logger.info("gRPC server stopped")

    def wait_for_termination(self) -> None:
        """Block until server terminates"""
        if self.server:
            self.server.wait_for_termination()
