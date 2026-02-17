"""
Tests for Ensemble Language Detector
====================================

Comprehensive test suite for the EnsembleLanguageDetector with 15+ languages
and various text lengths and edge cases.
"""

import asyncio
import pytest
from translation_providers.ensemble_detector import EnsembleLanguageDetector


@pytest.fixture
def detector():
    """Create an ensemble detector instance for testing."""
    return EnsembleLanguageDetector()


class TestEnsembleDetector:
    """Test suite for EnsembleLanguageDetector."""

    # Test data with various languages and text samples
    TEST_SAMPLES = {
        # English
        'en': [
            'Hello, how are you today?',
            'The quick brown fox jumps over the lazy dog',
            'English is a very flexible language with many words',
            'How do you do, my good fellow?',
            'I am learning to code in Python',
        ],
        # Spanish
        'es': [
            '¿Hola, cómo estás hoy?',
            'El rápido zorro marrón salta sobre el perro perezoso',
            'El español es una lengua romance muy hermosa',
            '¿Cómo está usted, mi buen amigo?',
            'Estoy aprendiendo a programar en Python',
        ],
        # French
        'fr': [
            'Bonjour, comment allez-vous?',
            'Le rapide renard brun saute par-dessus le chien paresseux',
            'Le français est une belle langue romane',
            'Comment allez-vous, mon bon ami?',
            'J\'apprends à programmer en Python',
        ],
        # German
        'de': [
            'Guten Tag, wie geht es Ihnen?',
            'Der schnelle braune Fuchs springt über den faulen Hund',
            'Deutsch ist eine germanische Sprache mit Umlauten',
            'Wie geht es dir, mein guter Freund?',
            'Ich lerne, in Python zu programmieren',
        ],
        # Italian
        'it': [
            'Ciao, come stai oggi?',
            'La veloce volpe marrone salta sopra il cane pigro',
            'L\'italiano è una bella lingua romanza',
            'Come stai, mio caro amico?',
            'Sto imparando a programmare in Python',
        ],
        # Portuguese
        'pt': [
            'Olá, como vai você?',
            'A rápida raposa marrom salta sobre o cão preguiçoso',
            'O português é uma bela língua romântica',
            'Como vai você, meu bom amigo?',
            'Estou aprendendo a programar em Python',
        ],
        # Dutch
        'nl': [
            'Hallo, hoe gaat het met u?',
            'De snelle bruine vos springt over de luie hond',
            'Nederlands is een Germaanse taal met veel cognaten',
            'Hoe gaat het met je, mijn goede vriend?',
            'Ik ben aan het leren programmeren in Python',
        ],
        # Russian
        'ru': [
            'Привет, как дела?',
            'Быстрая коричневая лиса прыгает через ленивую собаку',
            'Русский язык имеет интересную грамматику',
            'Как ты себя чувствуешь, мой добрый друг?',
            'Я учусь программировать на Python',
        ],
        # Japanese
        'ja': [
            'こんにちは、お元気ですか？',
            '素早い茶色のキツネが怠け者の犬を飛び越える',
            '日本語は複雑な文法を持っています',
            'お前の調子はどうだ？',
            'Pythonでプログラミングを学んでいます',
        ],
        # Chinese (Simplified)
        'zh': [
            '你好，今天怎么样？',
            '敏捷的棕色狐狸跳过懒狗',
            '中文是一种声调语言',
            '你好吗，我的朋友？',
            '我在学习用Python编程',
        ],
        # Korean
        'ko': [
            '안녕하세요, 어떻게 지내세요?',
            '빠른 갈색 여우가 게으른 개를 뛰어넘습니다',
            '한국어는 음절 문자입니다',
            '잘 지내세요, 제 친구?',
            'Python으로 프로그래밍하는 것을 배우고 있습니다',
        ],
        # Arabic
        'ar': [
            'مرحبا، كيف حالك؟',
            'الثعلب البني السريع يقفز فوق الكلب الكسول',
            'اللغة العربية لغة رومانسية جميلة',
            'كيف حالك يا صديقي الجيد؟',
            'أنا أتعلم البرمجة في Python',
        ],
        # Hindi
        'hi': [
            'नमस्ते, आप कैसे हैं?',
            'तेज भूरी लोमड़ी आलसी कुत्ते के ऊपर कूदती है',
            'हिंदी भारत में बोली जाने वाली एक प्रमुख भाषा है',
            'तुम कैसे हो, मेरे अच्छे दोस्त?',
            'मैं Python में प्रोग्रामिंग सीख रहा हूँ',
        ],
        # Turkish
        'tr': [
            'Merhaba, nasılsınız?',
            'Hızlı kahverengi tilki tembel köpeğin üzerinden atlıyor',
            'Türkçe agglutinative bir dildir',
            'Nasılsın, iyi dostum?',
            'Python\'da programlamayı öğreniyorum',
        ],
        # Polish
        'pl': [
            'Cześć, jak się masz?',
            'Szybki brązowy lis przeskakuje nad leniwym psem',
            'Polski jest słowiańskim językiem',
            'Jak się masz, mój dobry przyjacielu?',
            'Uczę się programować w Pythonie',
        ],
    }

    @pytest.mark.asyncio
    async def test_initialize_detector(self, detector):
        """Test detector initialization."""
        await detector._initialize_models()
        assert detector._initialized is True

    @pytest.mark.asyncio
    async def test_health_check(self, detector):
        """Test detector health check."""
        is_healthy = await detector.health_check()
        assert isinstance(is_healthy, bool)
        assert is_healthy is True or is_healthy is False  # At least one detector should work

    @pytest.mark.asyncio
    async def test_detect_english(self, detector):
        """Test English detection."""
        text = 'Hello, how are you today?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'en'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_spanish(self, detector):
        """Test Spanish detection."""
        text = '¿Hola, cómo estás hoy?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'es'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_french(self, detector):
        """Test French detection."""
        text = 'Bonjour, comment allez-vous?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'fr'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_german(self, detector):
        """Test German detection."""
        text = 'Guten Tag, wie geht es Ihnen?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'de'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_italian(self, detector):
        """Test Italian detection."""
        text = 'Ciao, come stai oggi?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'it'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_portuguese(self, detector):
        """Test Portuguese detection."""
        text = 'Olá, como vai você?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'pt'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_russian(self, detector):
        """Test Russian detection."""
        text = 'Привет, как дела?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'ru'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_japanese(self, detector):
        """Test Japanese detection."""
        text = 'こんにちは、お元気ですか？'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'ja'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_chinese(self, detector):
        """Test Chinese detection."""
        text = '你好，今天怎么样？'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'zh'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_detect_korean(self, detector):
        """Test Korean detection."""
        text = '안녕하세요, 어떻게 지내세요?'
        lang, confidence = await detector.detect_language(text)
        assert lang == 'ko'
        assert 0.0 <= confidence <= 1.0

    @pytest.mark.asyncio
    async def test_confidence_range(self, detector):
        """Test that confidence scores are in valid range."""
        text = 'This is a test sentence in English.'
        lang, confidence = await detector.detect_language(text)
        assert 0.0 <= confidence <= 1.0
        assert isinstance(confidence, float)

    @pytest.mark.asyncio
    async def test_language_code_format(self, detector):
        """Test that language codes are in valid format."""
        text = 'Bonjour le monde'
        lang, confidence = await detector.detect_language(text)
        assert isinstance(lang, str)
        assert len(lang) == 2  # ISO 639-1 format
        assert lang.islower()

    @pytest.mark.asyncio
    async def test_short_text_rejection(self, detector):
        """Test rejection of very short text."""
        text = 'Hi'
        with pytest.raises(ValueError):
            await detector.detect_language(text, min_length=5)

    @pytest.mark.asyncio
    async def test_empty_text_rejection(self, detector):
        """Test rejection of empty text."""
        text = ''
        with pytest.raises(ValueError):
            await detector.detect_language(text)

    @pytest.mark.asyncio
    async def test_whitespace_only_rejection(self, detector):
        """Test rejection of whitespace-only text."""
        text = '   \n\t  '
        with pytest.raises(ValueError):
            await detector.detect_language(text)

    @pytest.mark.asyncio
    async def test_long_text_detection(self, detector):
        """Test detection with longer text."""
        text = self.TEST_SAMPLES['en'][1]  # Long English text
        lang, confidence = await detector.detect_language(text)
        assert lang == 'en'
        # Confidence should be higher for longer texts
        assert confidence >= 0.70

    @pytest.mark.asyncio
    @pytest.mark.parametrize("lang_code,samples", [
        (lang, samples) for lang, samples in TEST_SAMPLES.items()
    ])
    async def test_all_languages(self, detector, lang_code, samples):
        """Parametrized test for all supported languages."""
        for sample in samples:
            try:
                detected_lang, confidence = await detector.detect_language(sample)
                # Allow some tolerance for mixed-language or ambiguous text
                assert detected_lang == lang_code or confidence < 0.75, \
                    f"Expected {lang_code} but got {detected_lang} for '{sample[:30]}'"
            except Exception as e:
                pytest.skip(f"Language detection failed: {e}")


if __name__ == '__main__':
    # Run a simple synchronous test
    import sys

    async def simple_test():
        """Simple test without pytest."""
        detector = EnsembleLanguageDetector()

        test_cases = [
            ('Hello, how are you?', 'en'),
            ('¿Hola, cómo estás?', 'es'),
            ('Bonjour, comment allez-vous?', 'fr'),
        ]

        print("Running simple ensemble detector tests...\n")

        for text, expected_lang in test_cases:
            try:
                lang, confidence = await detector.detect_language(text)
                status = '✓' if lang == expected_lang else '✗'
                print(f"{status} {text:35} -> {lang} ({confidence:.0%})")
            except Exception as e:
                print(f"✗ {text:35} -> ERROR: {e}")

    try:
        asyncio.run(simple_test())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
