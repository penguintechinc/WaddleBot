"""
gRPC Handler for Browser Source Core Module

Handles incoming gRPC requests for sending captions and overlay events
"""

import json
import logging
from datetime import datetime
from typing import Optional

import grpc
import jwt

from config import Config
from proto import browser_source_pb2, browser_source_pb2_grpc

logger = logging.getLogger(__name__)


class BrowserSourceServiceServicer(browser_source_pb2_grpc.BrowserSourceServiceServicer):
    """gRPC servicer for browser source operations"""

    def __init__(self, overlay_service, dal, caption_connections):
        """
        Initialize gRPC servicer

        Args:
            overlay_service: Overlay service instance
            dal: Database access layer instance
            caption_connections: Dictionary of caption WebSocket connections
        """
        self.overlay_service = overlay_service
        self.dal = dal
        self.caption_connections = caption_connections

    def _verify_token(self, token: str) -> tuple[bool, Optional[str]]:
        """
        Verify JWT token

        Args:
            token: JWT token string

        Returns:
            Tuple of (valid, error_message)
        """
        try:
            jwt.decode(
                token,
                Config.MODULE_SECRET_KEY,
                algorithms=[Config.JWT_ALGORITHM],
            )
            return True, None
        except jwt.ExpiredSignatureError:
            return False, "Token expired"
        except jwt.InvalidTokenError as e:
            return False, f"Invalid token: {str(e)}"

    async def SendCaption(
        self,
        request: browser_source_pb2.SendCaptionRequest,
        context: grpc.aio.ServicerContext,
    ) -> browser_source_pb2.SuccessResponse:
        """
        Send caption to browser source overlay

        Args:
            request: SendCaptionRequest with caption data
            context: gRPC service context

        Returns:
            SuccessResponse indicating success or failure
        """
        # Verify token
        valid, error = self._verify_token(request.token)
        if not valid:
            logger.warning(f"Token verification failed for SendCaption: {error}")
            return browser_source_pb2.SuccessResponse(
                success=False,
                error=f"Authentication failed: {error}"
            )

        try:
            community_id = request.community_id

            # Broadcast to WebSocket connections for this community
            if community_id in self.caption_connections:
                caption_payload = {
                    'type': 'caption',
                    'username': request.username,
                    'original': request.original_message,
                    'translated': request.translated_message,
                    'detected_lang': request.detected_language,
                    'target_lang': request.target_language,
                    'confidence': request.confidence,
                    'timestamp': datetime.utcnow().isoformat()
                }

                # Send to all connected websockets
                for ws in list(self.caption_connections.get(community_id, set())):
                    try:
                        await ws.send(json.dumps(caption_payload))
                    except Exception as ws_error:
                        logger.error(f"Error sending to websocket: {ws_error}")
                        self.caption_connections[community_id].discard(ws)

            # Store in database for recent history
            try:
                self.dal.executesql(
                    """INSERT INTO caption_events
                       (community_id, platform, username,
                        original_message, translated_message, detected_language,
                        target_language, confidence_score)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    [
                        community_id,
                        request.platform,
                        request.username,
                        request.original_message,
                        request.translated_message,
                        request.detected_language,
                        request.target_language,
                        request.confidence
                    ]
                )
                logger.info(f"Caption stored for community {community_id}")
            except Exception as db_error:
                logger.error(f"Failed to store caption event: {db_error}")

            return browser_source_pb2.SuccessResponse(
                success=True,
                message="Caption received and broadcasted successfully"
            )

        except Exception as e:
            logger.error(f"Error in SendCaption: {e}", exc_info=True)
            return browser_source_pb2.SuccessResponse(
                success=False,
                error=f"Internal server error: {str(e)}"
            )

    async def SendOverlayEvent(
        self,
        request: browser_source_pb2.SendOverlayEventRequest,
        context: grpc.aio.ServicerContext,
    ) -> browser_source_pb2.SuccessResponse:
        """
        Send overlay event to browser source

        Args:
            request: SendOverlayEventRequest with event data
            context: gRPC service context

        Returns:
            SuccessResponse indicating success or failure
        """
        # Verify token
        valid, error = self._verify_token(request.token)
        if not valid:
            logger.warning(f"Token verification failed for SendOverlayEvent: {error}")
            return browser_source_pb2.SuccessResponse(
                success=False,
                error=f"Authentication failed: {error}"
            )

        try:
            community_id = request.community_id

            # Broadcast event to WebSocket connections for this community
            if community_id in self.caption_connections:
                event_payload = {
                    'type': 'overlay_event',
                    'event_type': request.event_type,
                    'event_data': request.event_data,
                    'timestamp': datetime.utcnow().isoformat()
                }

                # Send to all connected websockets
                for ws in list(self.caption_connections.get(community_id, set())):
                    try:
                        await ws.send(json.dumps(event_payload))
                    except Exception as ws_error:
                        logger.error(f"Error sending event to websocket: {ws_error}")
                        self.caption_connections[community_id].discard(ws)

            logger.info(f"Overlay event '{request.event_type}' sent for community {community_id}")

            return browser_source_pb2.SuccessResponse(
                success=True,
                message="Overlay event sent successfully"
            )

        except Exception as e:
            logger.error(f"Error in SendOverlayEvent: {e}", exc_info=True)
            return browser_source_pb2.SuccessResponse(
                success=False,
                error=f"Internal server error: {str(e)}"
            )
