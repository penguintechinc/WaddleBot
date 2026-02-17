"""
Translation Provider Base Class
================================

Abstract base class for translation providers with standardized interface.
All translation providers must inherit from TranslationProvider and implement
the required async methods.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class TranslationResult:
    """
    Result of a translation operation.

    Attributes:
        original_text: The original text before translation
        translated_text: The translated text
        detected_lang: The detected language code (e.g., 'en', 'es')
        target_lang: The target language code
        confidence: Confidence score (0.0-1.0)
        provider: The name of the provider that performed the translation
        cached: Whether this result was retrieved from cache
    """
    original_text: str
    translated_text: str
    detected_lang: str
    target_lang: str
    confidence: float
    provider: str
    cached: bool = False


class TranslationProvider(ABC):
    """
    Abstract base class for translation providers.

    All translation provider implementations must inherit from this class
    and implement the required async methods for language detection and
    translation.
    """

    def __init__(self, provider_name: str):
        """
        Initialize the translation provider.

        Args:
            provider_name: Unique name for this provider
        """
        self.provider_name = provider_name
        logger.info(f"Initialized {self.__class__.__name__}")

    @abstractmethod
    async def detect_language(
        self,
        text: str
    ) -> Tuple[str, float]:
        """
        Detect the language of the given text.

        Args:
            text: Text to detect language for

        Returns:
            Tuple of (language_code, confidence_score)
            where confidence_score is between 0.0 and 1.0

        Raises:
            Exception: On detection failure
        """
        pass

    @abstractmethod
    async def translate(
        self,
        text: str,
        target_lang: str,
        source_lang: Optional[str] = None
    ) -> TranslationResult:
        """
        Translate text from source language to target language.

        Args:
            text: Text to translate
            target_lang: Target language code (e.g., 'es' for Spanish)
            source_lang: Optional source language code. If None, will be detected.

        Returns:
            TranslationResult object with translation details

        Raises:
            Exception: On translation failure
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the translation provider is healthy and available.

        Returns:
            True if provider is healthy, False otherwise
        """
        pass
