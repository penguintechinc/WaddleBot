"""
gRPC Handler for Translate Interaction Module

Implements the TranslateInteraction gRPC service, called by the router
in the hot message-processing path.
"""
import logging
from typing import Optional

import grpc
import jwt

from config import Config
from proto import translate_interaction_pb2, translate_interaction_pb2_grpc
from services.translation_service import TranslationService

logger = logging.getLogger(__name__)


class TranslateInteractionServicer(
    translate_interaction_pb2_grpc.TranslateInteractionServicer
):
    """gRPC servicer for translation operations."""

    def __init__(self, translation_service: TranslationService, dal):
        self.translation_service = translation_service
        self.dal = dal

    def _verify_token(self, token: str) -> tuple[bool, Optional[str]]:
        """Verify JWT token from router."""
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
            return False, str(e)

    async def Translate(self, request, context):
        """Hot-path translation call from router."""
        valid, err = self._verify_token(request.token)
        if not valid:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, err)
            return translate_interaction_pb2.TranslateResponse(
                success=False, error=err
            )

        try:
            config = await self._load_config(request.community_id)
            result = await self.translation_service.translate(
                text=request.text,
                target_lang=request.target_lang,
                community_id=request.community_id,
                config=config,
                platform=request.platform,
                channel_id=request.channel_id,
            )
            if result is None:
                return translate_interaction_pb2.TranslateResponse(
                    success=True,
                    skipped=True,
                    skip_reason="translation not needed",
                )
            return translate_interaction_pb2.TranslateResponse(
                success=True,
                skipped=False,
                translated_text=result.get('translated_text', ''),
                original_text=result.get('original_text', request.text),
                detected_lang=result.get('detected_lang', ''),
                target_lang=result.get('target_lang', request.target_lang),
                confidence=float(result.get('confidence', 0.0)),
                provider=result.get('provider', ''),
                cached=bool(result.get('cached', False)),
                tokens_preserved=int(result.get('tokens_preserved', 0)),
            )
        except Exception as e:
            logger.error(f"gRPC Translate error: {e}", exc_info=True)
            return translate_interaction_pb2.TranslateResponse(
                success=False, error=str(e)
            )

    async def DetectLanguage(self, request, context):
        """Language detection without translation."""
        valid, err = self._verify_token(request.token)
        if not valid:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, err)
            return translate_interaction_pb2.DetectLanguageResponse(
                success=False, error=err
            )
        try:
            lang, confidence = await self.translation_service._detect_language(
                request.text
            )
            return translate_interaction_pb2.DetectLanguageResponse(
                success=True,
                detected_lang=lang,
                confidence=float(confidence),
            )
        except Exception as e:
            logger.error(f"gRPC DetectLanguage error: {e}", exc_info=True)
            return translate_interaction_pb2.DetectLanguageResponse(
                success=False, error=str(e)
            )

    async def CleanupCache(self, request, context):
        """Trigger cache maintenance."""
        valid, err = self._verify_token(request.token)
        if not valid:
            await context.abort(grpc.StatusCode.UNAUTHENTICATED, err)
            return translate_interaction_pb2.CleanupCacheResponse(
                success=False, error=err
            )
        try:
            await self.translation_service.cleanup_cache()
            return translate_interaction_pb2.CleanupCacheResponse(
                success=True, message="Cache cleanup complete"
            )
        except Exception as e:
            return translate_interaction_pb2.CleanupCacheResponse(
                success=False, error=str(e)
            )

    async def _load_config(self, community_id: str) -> dict:
        """Load community translation settings from DB."""
        if self.dal is None:
            return {}
        try:
            rows = self.dal(
                self.dal.community_translation_settings.community_id == community_id
            ).select()
            if rows:
                row = rows[0]
                return {
                    'enabled': row.enabled,
                    'target_language': row.target_language,
                    'confidence_threshold': row.confidence_threshold,
                    'min_words': row.min_words,
                    'detection_method': row.detection_method,
                    'google_api_key': row.google_api_key,
                    'preprocessing': row.preprocessing,
                    'captions': row.captions,
                    'ai_decision': row.ai_decision,
                }
        except Exception as e:
            logger.warning(f"Could not load config for {community_id}: {e}")
        return {}
