"""
Google Cloud Translate API Provider
====================================

Translation provider using the Google Cloud Translate API.

Features:
- Official Google Cloud API (more reliable)
- Requires API key/credentials
- Higher accuracy than googletrans
- Supports advanced features (custom glossaries, document translation)
- Runs in executor to avoid blocking
"""

import asyncio
import logging
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from google.cloud import translate_v2
import google.auth.exceptions

from .base_provider import TranslationProvider, TranslationResult

logger = logging.getLogger(__name__)


class GoogleCloudProvider(TranslationProvider):
    """
    Google Cloud Translate API provider.

    This provider uses the official Google Cloud Translate API and requires
    proper credentials. All blocking operations are run in an executor to
    avoid blocking the event loop.
    """

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        project_id: Optional[str] = None,
        executor: Optional[ThreadPoolExecutor] = None
    ):
        """
        Initialize the Google Cloud Translate provider.

        Args:
            credentials_path: Path to Google Cloud credentials JSON file.
                             If None, uses GOOGLE_APPLICATION_CREDENTIALS env var.
            project_id: Google Cloud project ID.
                       If None, extracted from credentials.
            executor: Optional ThreadPoolExecutor for blocking operations.
                     If None, a default executor will be used.

        Raises:
            ValueError: If credentials cannot be loaded
            google.auth.exceptions.GoogleAuthError: If authentication fails
        """
        super().__init__("google_cloud")

        self.credentials_path = credentials_path
        self.project_id = project_id
        self.executor = executor

        try:
            # Initialize Google Cloud Translate client
            self.client = translate_v2.Client(
                credentials_path=credentials_path,
                project_id=project_id
            )

            logger.info(
                f"Initialized GoogleCloudProvider "
                f"(project: {self.client.project_id or 'auto'})"
            )

        except google.auth.exceptions.GoogleAuthError as e:
            logger.error(f"Google Cloud authentication failed: {e}")
            raise ValueError(f"Failed to initialize Google Cloud Translate: {e}")

        except Exception as e:
            logger.error(f"Failed to initialize Google Cloud Translate: {e}")
            raise

    async def detect_language(
        self,
        text: str
    ) -> Tuple[str, float]:
        """
        Detect the language of the given text using Google Cloud API.

        Args:
            text: Text to detect language for

        Returns:
            Tuple of (language_code, confidence_score)

        Raises:
            ValueError: If text is empty
            Exception: On detection failure
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            # Run detection in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._detect_sync,
                text
            )
            return result

        except Exception as e:
            logger.error(f"Language detection failed: {e}", exc_info=True)
            raise

    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate text using Google Cloud Translate API.

        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Optional source language code. If None, will be detected.

        Returns:
            TranslationResult with translation details

        Raises:
            ValueError: If text or target_lang is empty
            Exception: On translation failure
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        if not target_lang or not target_lang.strip():
            raise ValueError("Target language cannot be empty")

        try:
            # Detect source language if not provided
            if not source_lang:
                detected_lang, confidence = await self.detect_language(text)
                source_lang = detected_lang
            else:
                confidence = 1.0

            # Run translation in executor to avoid blocking
            loop = asyncio.get_event_loop()
            translated = await loop.run_in_executor(
                self.executor,
                self._translate_sync,
                text,
                target_lang,
                source_lang
            )

            logger.info(
                f"Translated {source_lang} -> {target_lang} via Google Cloud: "
                f"'{text[:50]}...' -> '{translated[:50]}...'"
            )

            return TranslationResult(
                original_text=text,
                translated_text=translated,
                detected_lang=source_lang,
                target_lang=target_lang,
                confidence=confidence,
                provider=self.provider_name,
                cached=False
            )

        except Exception as e:
            logger.error(
                f"Translation failed: {e}",
                exc_info=True
            )
            raise

    async def health_check(self) -> bool:
        """
        Check if Google Cloud Translate API is accessible.

        This performs a simple test translation to verify connectivity.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Test with a simple translation
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self.executor,
                self._translate_sync,
                "Hello",
                "es",
                "en"
            )

            is_healthy = result and isinstance(result, str)

            if is_healthy:
                logger.debug("GoogleCloudProvider health check passed")
            else:
                logger.warning(
                    "GoogleCloudProvider health check returned invalid result"
                )

            return is_healthy

        except Exception as e:
            logger.error(
                f"GoogleCloudProvider health check failed: {e}",
                exc_info=True
            )
            return False

    def _detect_sync(self, text: str) -> Tuple[str, float]:
        """
        Synchronous language detection wrapper.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence_score)
        """
        try:
            result = self.client.detect_language(text)

            # result is a dict with 'language' and 'confidence' keys
            language = result.get('language', 'unknown')
            confidence = result.get('confidence', 0.8)

            # Normalize confidence to 0.0-1.0
            if isinstance(confidence, (int, float)):
                confidence = min(1.0, max(0.0, float(confidence)))
            else:
                confidence = 0.8

            return (language, confidence)

        except Exception as e:
            logger.error(f"Sync detection error: {e}")
            raise

    def _translate_sync(
        self,
        text: str,
        target_lang: str,
        source_lang: str
    ) -> str:
        """
        Synchronous translation wrapper.

        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code

        Returns:
            Translated text
        """
        try:
            result = self.client.translate_text(
                text,
                source_language=source_lang,
                target_language=target_lang
            )

            # result is a dict with 'translatedText' key
            translated_text = result.get('translatedText', '')

            return translated_text

        except Exception as e:
            logger.error(f"Sync translation error: {e}")
            raise
