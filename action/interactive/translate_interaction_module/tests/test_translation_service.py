#!/usr/bin/env python3
"""
Comprehensive unit tests for TranslationService.

Tests cover:
- Language detection for 12 languages
- Translation between key language pairs
- Skip condition handling
- Provider fallback behavior
- Multi-level caching (memory, Redis, database)
- Error handling and edge cases
"""

import pytest
import json
import hashlib
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, timezone

from services.translation_service import TranslationService
from services.translation_providers.base_provider import TranslationResult


# Test data for 12 languages
ENGLISH_TEXT = "Hello, how are you doing today?"
SPANISH_TEXT = "Hola, ¿cómo estás hoy?"
FRENCH_TEXT = "Bonjour, comment allez-vous aujourd'hui?"
GERMAN_TEXT = "Hallo, wie geht es dir heute?"
JAPANESE_TEXT = "こんにちは、今日はどうですか？"
KOREAN_TEXT = "안녕하세요, 오늘 어떻게 지내세요?"
CHINESE_TEXT = "你好，你今天过得怎么样？"
PORTUGUESE_TEXT = "Olá, como você está hoje?"
RUSSIAN_TEXT = "Привет, как дела сегодня?"
ARABIC_TEXT = "مرحبا، كيف حالك اليوم؟"
HINDI_TEXT = "नमस्ते, आप आज कैसे हैं?"
ITALIAN_TEXT = "Ciao, come stai oggi?"


class TestLanguageDetection:
    """Test language detection for 12 languages."""

    @pytest.mark.asyncio
    async def test_language_detection_english(self):
        """Test English language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # Mock provider
        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('en', 0.95))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(ENGLISH_TEXT)

        assert lang == 'en'
        assert confidence > 0.7
        provider_mock.detect_language.assert_called_once_with(ENGLISH_TEXT)

    @pytest.mark.asyncio
    async def test_language_detection_spanish(self):
        """Test Spanish language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(SPANISH_TEXT)

        assert lang == 'es'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_french(self):
        """Test French language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('fr', 0.91))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(FRENCH_TEXT)

        assert lang == 'fr'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_german(self):
        """Test German language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('de', 0.89))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(GERMAN_TEXT)

        assert lang == 'de'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_japanese(self):
        """Test Japanese language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('ja', 0.88))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(JAPANESE_TEXT)

        assert lang == 'ja'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_korean(self):
        """Test Korean language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('ko', 0.87))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(KOREAN_TEXT)

        assert lang == 'ko'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_chinese(self):
        """Test Chinese language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('zh', 0.86))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(CHINESE_TEXT)

        assert lang == 'zh'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_portuguese(self):
        """Test Portuguese language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('pt', 0.90))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(PORTUGUESE_TEXT)

        assert lang == 'pt'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_russian(self):
        """Test Russian language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('ru', 0.93))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(RUSSIAN_TEXT)

        assert lang == 'ru'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_arabic(self):
        """Test Arabic language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('ar', 0.85))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(ARABIC_TEXT)

        assert lang == 'ar'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_hindi(self):
        """Test Hindi language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('hi', 0.84))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(HINDI_TEXT)

        assert lang == 'hi'
        assert confidence > 0.7

    @pytest.mark.asyncio
    async def test_language_detection_italian(self):
        """Test Italian language detection."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('it', 0.91))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        lang, confidence = await service._detect_language(ITALIAN_TEXT)

        assert lang == 'it'
        assert confidence > 0.7


class TestTranslation:
    """Test translation between key language pairs."""

    @pytest.mark.asyncio
    async def test_translate_spanish_to_english(self):
        """Test Spanish to English translation."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # Mock the provider
        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        # Mock cache misses
        cache_mock.get = AsyncMock(return_value=None)
        dal_mock.executesql = MagicMock(return_value=None)

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        assert result is not None
        assert result['target_lang'] == 'en'
        assert result['detected_lang'] == 'es'
        assert 'Hello' in result['translated_text'] or result['translated_text']
        assert result['provider'] == 'googletrans'
        assert result['cached'] == False

    @pytest.mark.asyncio
    async def test_translate_french_to_english(self):
        """Test French to English translation."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('fr', 0.91))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=FRENCH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='fr',
            target_lang='en',
            confidence=0.91,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        dal_mock.executesql = MagicMock(return_value=None)

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(FRENCH_TEXT, 'en', 123, config)

        assert result is not None
        assert result['detected_lang'] == 'fr'
        assert result['target_lang'] == 'en'

    @pytest.mark.asyncio
    async def test_translate_german_to_english(self):
        """Test German to English translation."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('de', 0.89))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=GERMAN_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='de',
            target_lang='en',
            confidence=0.89,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        dal_mock.executesql = MagicMock(return_value=None)

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(GERMAN_TEXT, 'en', 123, config)

        assert result is not None
        assert result['detected_lang'] == 'de'
        assert result['target_lang'] == 'en'

    @pytest.mark.asyncio
    async def test_translate_japanese_to_english(self):
        """Test Japanese to English translation."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('ja', 0.88))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=JAPANESE_TEXT,
            translated_text="Hello, how are you?",
            detected_lang='ja',
            target_lang='en',
            confidence=0.88,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        dal_mock.executesql = MagicMock(return_value=None)

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(JAPANESE_TEXT, 'en', 123, config)

        assert result is not None
        assert result['detected_lang'] == 'ja'
        assert result['target_lang'] == 'en'


class TestSkipConditions:
    """Test skip condition handling."""

    @pytest.mark.asyncio
    async def test_skip_condition_too_short(self):
        """Test skipping when message is too short."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        config = {
            'enabled': True,
            'min_words': 5
        }

        result = await service.translate("Hi", 'en', 123, config)

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_condition_low_confidence(self):
        """Test skipping when language detection confidence is too low."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # Mock provider with low confidence
        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('unknown', 0.3))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate("Hello world", 'en', 123, config)

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_condition_already_target_language(self):
        """Test skipping when text is already in target language."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('en', 0.95))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(ENGLISH_TEXT, 'en', 123, config)

        assert result is None

    @pytest.mark.asyncio
    async def test_skip_condition_disabled(self):
        """Test skipping when translation is disabled."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        config = {
            'enabled': False,
            'min_words': 2
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        assert result is None


class TestProviderFallback:
    """Test provider fallback behavior."""

    @pytest.mark.asyncio
    async def test_provider_fallback_googletrans_to_google_cloud(self):
        """Test fallback from GoogleTrans to Google Cloud."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # GoogleTrans fails, Google Cloud succeeds
        googletrans_mock = AsyncMock()
        googletrans_mock.health_check = AsyncMock(return_value=True)
        googletrans_mock.translate = AsyncMock(side_effect=Exception("API error"))

        google_cloud_mock = AsyncMock()
        google_cloud_mock.health_check = AsyncMock(return_value=True)
        google_cloud_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='google_cloud'
        ))

        service._providers = {
            'google_cloud': google_cloud_mock,
            'googletrans': googletrans_mock
        }
        service._providers_initialized = True

        result = await service._translate_with_fallback(
            SPANISH_TEXT, 'es', 'en', 0.92
        )

        assert result is not None
        assert result.provider == 'google_cloud'

    @pytest.mark.asyncio
    async def test_provider_fallback_googletrans_to_waddleai(self):
        """Test fallback from GoogleTrans to WaddleAI."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # GoogleTrans fails, WaddleAI succeeds
        googletrans_mock = AsyncMock()
        googletrans_mock.health_check = AsyncMock(return_value=True)
        googletrans_mock.translate = AsyncMock(side_effect=Exception("API error"))

        waddleai_mock = AsyncMock()
        waddleai_mock.health_check = AsyncMock(return_value=True)
        waddleai_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='waddleai'
        ))

        service._providers = {
            'googletrans': googletrans_mock,
            'waddleai': waddleai_mock
        }
        service._providers_initialized = True

        result = await service._translate_with_fallback(
            SPANISH_TEXT, 'es', 'en', 0.92
        )

        assert result is not None
        assert result.provider == 'waddleai'

    @pytest.mark.asyncio
    async def test_provider_fallback_all_fail(self):
        """Test when all providers fail."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # All providers fail
        googletrans_mock = AsyncMock()
        googletrans_mock.health_check = AsyncMock(return_value=True)
        googletrans_mock.translate = AsyncMock(side_effect=Exception("API error"))

        waddleai_mock = AsyncMock()
        waddleai_mock.health_check = AsyncMock(return_value=True)
        waddleai_mock.translate = AsyncMock(side_effect=Exception("API error"))

        service._providers = {
            'googletrans': googletrans_mock,
            'waddleai': waddleai_mock
        }
        service._providers_initialized = True

        result = await service._translate_with_fallback(
            SPANISH_TEXT, 'es', 'en', 0.92
        )

        assert result is None


class TestCaching:
    """Test multi-level caching behavior."""

    @pytest.mark.asyncio
    async def test_cache_miss_then_hit(self):
        """Test cache miss followed by cache hit."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        cache_mock.set = AsyncMock()
        dal_mock.executesql = MagicMock(return_value=None)
        dal_mock.commit = MagicMock()

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        # First call - cache miss
        result1 = await service.translate(SPANISH_TEXT, 'en', 123, config)
        assert result1 is not None
        assert result1['cached'] == False

        # Second call - memory cache hit
        result2 = await service.translate(SPANISH_TEXT, 'en', 123, config)
        assert result2 is not None
        assert result2['cached'] == True
        assert result1['translated_text'] == result2['translated_text']

    @pytest.mark.asyncio
    async def test_cache_stores_in_all_levels(self):
        """Test that cache stores in memory, Redis, and database."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        cache_mock.set = AsyncMock()
        dal_mock.executesql = MagicMock(return_value=None)
        dal_mock.commit = MagicMock()

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        # Verify Redis cache was called
        assert cache_mock.set.called

        # Verify database cache was called
        assert dal_mock.executesql.called
        assert dal_mock.commit.called

        # Verify memory cache has the result
        cache_key = service._get_cache_key(SPANISH_TEXT, 'es', 'en')
        assert cache_key in service._memory_cache

    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation is consistent."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # Generate cache keys
        key1 = service._get_cache_key(SPANISH_TEXT, 'es', 'en')
        key2 = service._get_cache_key(SPANISH_TEXT, 'es', 'en')
        key3 = service._get_cache_key(SPANISH_TEXT, 'es', 'fr')

        # Same input should generate same key
        assert key1 == key2

        # Different target language should generate different key
        assert key1 != key3

        # Key should be SHA-256 hash (64 characters)
        assert len(key1) == 64
        assert isinstance(key1, str)


class TestErrorHandling:
    """Test error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_invalid_language_code(self):
        """Test handling of invalid language code."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(
            side_effect=Exception("Invalid language code")
        )

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'invalid', 123, config)

        # Should handle gracefully and return None
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Test handling of empty message."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        config = {
            'enabled': True,
            'min_words': 2
        }

        result = await service.translate("", 'en', 123, config)

        assert result is None

    @pytest.mark.asyncio
    async def test_very_long_message(self):
        """Test handling of very long message."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('en', 0.95))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text="word " * 10000,
            translated_text="palabra " * 10000,
            detected_lang='en',
            target_lang='es',
            confidence=0.95,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        cache_mock.set = AsyncMock()
        dal_mock.executesql = MagicMock(return_value=None)
        dal_mock.commit = MagicMock()

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        long_text = "word " * 10000
        result = await service.translate(long_text, 'es', 123, config)

        # Should handle without error
        assert result is not None


class TestLanguageDetectionFallback:
    """Test language detection with provider fallback."""

    @pytest.mark.asyncio
    async def test_language_detection_provider_fallback(self):
        """Test language detection falls back between providers."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # First provider fails, second succeeds
        provider1_mock = AsyncMock()
        provider1_mock.detect_language = AsyncMock(
            side_effect=Exception("Provider 1 error")
        )

        provider2_mock = AsyncMock()
        provider2_mock.detect_language = AsyncMock(return_value=('es', 0.92))

        service._providers = {
            'provider1': provider1_mock,
            'provider2': provider2_mock
        }
        service._providers_initialized = True

        lang, confidence = await service._detect_language(SPANISH_TEXT)

        assert lang == 'es'
        assert confidence == 0.92

    @pytest.mark.asyncio
    async def test_language_detection_all_providers_fail(self):
        """Test language detection when all providers fail."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # All providers fail
        provider1_mock = AsyncMock()
        provider1_mock.detect_language = AsyncMock(
            side_effect=Exception("Provider 1 error")
        )

        provider2_mock = AsyncMock()
        provider2_mock.detect_language = AsyncMock(
            side_effect=Exception("Provider 2 error")
        )

        service._providers = {
            'provider1': provider1_mock,
            'provider2': provider2_mock
        }
        service._providers_initialized = True

        lang, confidence = await service._detect_language(SPANISH_TEXT)

        assert lang == 'unknown'
        assert confidence == 0.0


class TestProviderHealthCheck:
    """Test provider health check handling."""

    @pytest.mark.asyncio
    async def test_provider_skipped_on_health_check_failure(self):
        """Test provider is skipped if health check fails."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # First provider fails health check
        provider1_mock = AsyncMock()
        provider1_mock.health_check = AsyncMock(return_value=False)

        # Second provider succeeds
        provider2_mock = AsyncMock()
        provider2_mock.health_check = AsyncMock(return_value=True)
        provider2_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello, how are you doing today?",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='provider2'
        ))

        service._providers = {
            'provider1': provider1_mock,
            'provider2': provider2_mock
        }
        service._providers_initialized = True

        result = await service._translate_with_fallback(
            SPANISH_TEXT, 'es', 'en', 0.92
        )

        assert result is not None
        assert result.provider == 'provider2'
        provider1_mock.health_check.assert_called_once()
        provider2_mock.health_check.assert_called_once()


class TestRedisCache:
    """Test Redis cache functionality."""

    @pytest.mark.asyncio
    async def test_redis_cache_hit(self):
        """Test retrieving translation from Redis cache."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        # Simulate Redis cache hit
        cached_result = {
            'translated_text': 'Hello world',
            'detected_lang': 'es',
            'target_lang': 'en',
            'confidence': 0.92,
            'provider': 'googletrans',
            'cached': True
        }
        cache_mock.get = AsyncMock(return_value=json.dumps(cached_result))
        cache_mock.set = AsyncMock()
        dal_mock.executesql = MagicMock(return_value=None)

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        assert result is not None
        assert result['cached'] == True
        assert result['translated_text'] == 'Hello world'

    @pytest.mark.asyncio
    async def test_redis_cache_set_on_new_translation(self):
        """Test Redis cache is set when translation is performed."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello world",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        cache_mock.set = AsyncMock()
        dal_mock.executesql = MagicMock(return_value=None)
        dal_mock.commit = MagicMock()

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        assert result is not None
        # Verify Redis cache set was called
        assert cache_mock.set.called

        # Check call arguments
        call_args = cache_mock.set.call_args
        assert 'translation:' in call_args[0][0]  # Key should start with 'translation:'
        assert call_args[1]['ttl'] == 86400  # 24 hours


class TestDatabaseCache:
    """Test database cache functionality."""

    @pytest.mark.asyncio
    async def test_db_cache_retrieval(self):
        """Test retrieving translation from database cache."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        cache_mock.set = AsyncMock()

        # Simulate database cache hit
        dal_mock.executesql = MagicMock(return_value=[
            ('Hello world', 'googletrans', 0.92)
        ])
        dal_mock.commit = MagicMock()

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        assert result is not None
        assert result['cached'] == True
        assert result['translated_text'] == 'Hello world'

    @pytest.mark.asyncio
    async def test_db_cache_store_on_new_translation(self):
        """Test database cache is stored when translation is performed."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.92))
        provider_mock.health_check = AsyncMock(return_value=True)
        provider_mock.translate = AsyncMock(return_value=TranslationResult(
            original_text=SPANISH_TEXT,
            translated_text="Hello world",
            detected_lang='es',
            target_lang='en',
            confidence=0.92,
            provider='googletrans'
        ))

        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        cache_mock.get = AsyncMock(return_value=None)
        cache_mock.set = AsyncMock()
        dal_mock.executesql = MagicMock(return_value=None)
        dal_mock.commit = MagicMock()

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.7
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)

        assert result is not None
        # Verify database cache store was called
        assert dal_mock.executesql.called
        assert dal_mock.commit.called


class TestConfigurationHandling:
    """Test configuration handling."""

    @pytest.mark.asyncio
    async def test_config_min_words_threshold(self):
        """Test min_words configuration is respected."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        config = {
            'enabled': True,
            'min_words': 10
        }

        # Only 5 words - should be skipped
        result = await service.translate("one two three four five", 'en', 123, config)
        assert result is None

    @pytest.mark.asyncio
    async def test_config_confidence_threshold(self):
        """Test confidence_threshold configuration is respected."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        provider_mock = AsyncMock()
        provider_mock.detect_language = AsyncMock(return_value=('es', 0.5))
        service._providers = {'googletrans': provider_mock}
        service._providers_initialized = True

        config = {
            'enabled': True,
            'min_words': 2,
            'confidence_threshold': 0.9
        }

        # Confidence 0.5 below threshold 0.9 - should be skipped
        result = await service.translate(SPANISH_TEXT, 'en', 123, config)
        assert result is None

    @pytest.mark.asyncio
    async def test_config_enabled_flag(self):
        """Test enabled configuration flag."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        config = {
            'enabled': False,
            'min_words': 2
        }

        result = await service.translate(SPANISH_TEXT, 'en', 123, config)
        assert result is None


class TestCacheStatistics:
    """Test cache statistics functionality."""

    @pytest.mark.asyncio
    async def test_get_cache_stats(self):
        """Test retrieving cache statistics."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        # Add some entries to memory cache
        service._memory_cache['key1'] = {'text': 'value1'}
        service._memory_cache['key2'] = {'text': 'value2'}

        # Mock database query
        dal_mock.executesql = MagicMock(return_value=[(100, 25)])

        stats = await service.get_cache_stats()

        assert 'memory_cache_size' in stats
        assert 'memory_cache_max_size' in stats
        assert stats['memory_cache_size'] == 2
        assert stats['memory_cache_max_size'] == 1000
        assert stats['db_cache_total_entries'] == 100
        assert stats['db_cache_high_use_entries'] == 25


class TestCacheCleanup:
    """Test cache cleanup functionality."""

    @pytest.mark.asyncio
    async def test_cleanup_cache(self):
        """Test cache cleanup."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        dal_mock.executesql = MagicMock(return_value=None)
        dal_mock.commit = MagicMock()

        result = await service.cleanup_cache()

        assert result['success'] == True
        dal_mock.executesql.assert_called_once()
        dal_mock.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_cache_error_handling(self):
        """Test cache cleanup error handling."""
        dal_mock = MagicMock()
        cache_mock = AsyncMock()

        service = TranslationService(dal_mock, cache_mock)

        dal_mock.executesql = MagicMock(
            side_effect=Exception("Database error")
        )

        result = await service.cleanup_cache()

        assert result['success'] == False
        assert 'error' in result
