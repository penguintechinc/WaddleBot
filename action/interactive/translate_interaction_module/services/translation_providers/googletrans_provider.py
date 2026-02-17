"""
Google Translate Free Provider
===============================

Translation provider using the deep-translator library.

Features:
- Free translation without API key
- Uses Google Translate under the hood
- Language detection via langdetect
- Runs in executor to avoid blocking
"""

import asyncio
import logging
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from deep_translator import GoogleTranslator
from langdetect import detect, detect_langs

from .base_provider import TranslationProvider, TranslationResult

logger = logging.getLogger(__name__)


class GoogleTransProvider(TranslationProvider):
    """
    Free Google Translate provider using deep-translator library.

    This provider uses Google's translation service via deep-translator
    and does not require an API key. All blocking operations are run
    in an executor to avoid blocking the event loop.
    """

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None):
        """
        Initialize the Google Translate provider.

        Args:
            executor: Optional ThreadPoolExecutor for blocking operations.
                     If None, a default executor will be used.
        """
        super().__init__("googletrans")
        self.executor = executor
        logger.info("Initialized GoogleTransProvider (deep-translator)")

    async def detect_language(
        self,
        text: str
    ) -> Tuple[str, float]:
        """
        Detect the language of the given text using langdetect.

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
        Translate text using Google Translate via deep-translator.

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
                f"Translated {source_lang} -> {target_lang}: "
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
        Check if Google Translate is accessible.

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
                logger.debug("GoogleTransProvider health check passed")
            else:
                logger.warning("GoogleTransProvider health check returned invalid result")

            return is_healthy

        except Exception as e:
            logger.error(
                f"GoogleTransProvider health check failed: {e}",
                exc_info=True
            )
            return False

    def _detect_sync(self, text: str) -> Tuple[str, float]:
        """
        Synchronous language detection using langdetect.

        Args:
            text: Text to detect

        Returns:
            Tuple of (language_code, confidence_score)
        """
        try:
            # Use detect_langs for confidence score
            detections = detect_langs(text)
            if detections:
                top_detection = detections[0]
                lang_code = top_detection.lang
                confidence = top_detection.prob
                return (lang_code, min(1.0, max(0.0, confidence)))
            else:
                # Fallback to simple detect
                lang_code = detect(text)
                return (lang_code, 0.8)

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
        Synchronous translation using deep-translator.

        Args:
            text: Text to translate
            target_lang: Target language code
            source_lang: Source language code

        Returns:
            Translated text
        """
        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            translated_text = translator.translate(text)
            return translated_text

        except Exception as e:
            logger.error(f"Sync translation error: {e}")
            raise
