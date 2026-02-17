"""
Ensemble Language Detector
==========================

Multi-library language detection combining fastText, Lingua, and langdetect
for high-confidence language identification.

Strategy:
---------
1. Preprocess text: Remove @mentions, URLs, emotes, commands to reduce noise
2. FastText (primary): Fast, good for longer texts (>30 chars)
3. Lingua (accuracy): High accuracy, especially for short texts
4. Langdetect (validation): Additional confidence validation

Consensus Logic:
- All 3 agree: confidence = 0.95
- 2 of 3 agree: confidence = 0.85
- 1 agrees (ties broken by fastText > lingua > langdetect): confidence = 0.70

Performance Targets:
- <50ms per detection (fastText is very fast)
- Support 12+ languages
- Cache detection results alongside translation cache

Preprocessing:
- Strips @mentions, URLs, !commands, emotes before detection
- Minimum 10 chars of actual text required for reliable detection
"""

import asyncio
import logging
import re
import os
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Regex patterns for text preprocessing
MENTION_PATTERN = re.compile(r'@\w+', re.UNICODE)
URL_PATTERN = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
COMMAND_PATTERN = re.compile(r'!\w+', re.UNICODE)
# Common Twitch/Discord emotes (text-based)
EMOTE_PATTERN = re.compile(r'\b(Kappa|PogChamp|LUL|LULW|KEKW|Pepega|monkaS|OMEGALUL|PepeHands|FeelsBadMan|FeelsGoodMan|4Head|EleGiggle|BibleThump|ResidentSleeper|Jebaited|NotLikeThis|WutFace|Kreygasm|HeyGuys|VoHiYo|BloodTrail|CoolStoryBob|DansGame|TriHard|cmonBruh|Clap|POGGERS|widepeepoHappy|peepoSad|HYPERS|5Head|Sadge|copium|Copium)\b', re.IGNORECASE)
# Unicode emoji pattern (simplified - catches most common emoji ranges)
EMOJI_PATTERN = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001F900-\U0001F9FF]+', re.UNICODE)


class EnsembleLanguageDetector:
    """
    Ensemble detector using fastText, Lingua, and langdetect.

    Combines three language detection libraries for high-confidence language
    identification with fallback mechanisms for reliability.
    """

    # Language code mappings for consistency
    LANGUAGE_MAPPINGS = {
        'en': 'en',
        'es': 'es',
        'fr': 'fr',
        'de': 'de',
        'it': 'it',
        'pt': 'pt',
        'nl': 'nl',
        'ru': 'ru',
        'ja': 'ja',
        'zh': 'zh',
        'ko': 'ko',
        'ar': 'ar',
        'hi': 'hi',
        'tr': 'tr',
        'pl': 'pl',
    }

    # Minimum cleaned text length for reliable detection
    MIN_TEXT_LENGTH = 10

    # FastText model path (download from Facebook AI)
    FASTTEXT_MODEL_PATH = os.getenv(
        'FASTTEXT_MODEL_PATH',
        '/app/models/lid.176.bin'
    )

    def __init__(self, executor: Optional[ThreadPoolExecutor] = None):
        """
        Initialize the Ensemble Language Detector.

        Args:
            executor: Optional ThreadPoolExecutor for blocking operations.
                     If None, a default executor will be used.
        """
        self.executor = executor
        self.fasttext_model = None
        self.lingua_detector = None
        self.langdetect_ready = False

        logger.info("EnsembleLanguageDetector initialized")

        # Initialize libraries asynchronously (lazy load on first use)
        self._initialized = False

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Preprocess text by removing noise that interferes with detection.

        Removes:
        - @mentions (e.g., @penguinzplays)
        - URLs (http://, https://, www.)
        - !commands (e.g., !help, !points)
        - Common Twitch/Discord emotes (Kappa, PogChamp, etc.)
        - Unicode emojis

        Args:
            text: Raw input text

        Returns:
            Cleaned text suitable for language detection
        """
        cleaned = text

        # Remove patterns in order
        cleaned = MENTION_PATTERN.sub('', cleaned)
        cleaned = URL_PATTERN.sub('', cleaned)
        cleaned = COMMAND_PATTERN.sub('', cleaned)
        cleaned = EMOTE_PATTERN.sub('', cleaned)
        cleaned = EMOJI_PATTERN.sub('', cleaned)

        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())

        return cleaned.strip()

    async def _initialize_models(self) -> None:
        """
        Lazy initialization of language detection models.

        Runs blocking imports in executor to avoid blocking event loop.
        """
        if self._initialized:
            return

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            self.executor,
            self._initialize_models_sync
        )
        self._initialized = True

    def _initialize_models_sync(self) -> None:
        """
        Synchronous initialization of models (runs in executor).
        """
        try:
            # Initialize fastText (optional - requires native build)
            import fasttext
            fasttext.FastText.eprint = lambda x: None  # Suppress fastText output

            # Load fastText language identification model
            # Download from: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin
            model_path = self.FASTTEXT_MODEL_PATH
            if os.path.exists(model_path):
                self.fasttext_model = fasttext.load_model(model_path)
                logger.info(f"FastText language model loaded from {model_path}")
            else:
                logger.warning(
                    f"FastText model not found at '{model_path}'. "
                    "Download from: https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
                )
        except ImportError:
            logger.info("fasttext-wheel not installed (optional). Using Lingua + langdetect for ensemble.")

        try:
            # Initialize Lingua (high accuracy detector)
            from lingua import Language, LanguageDetectorBuilder

            # Build detector with common languages
            languages = [
                Language.ENGLISH, Language.SPANISH, Language.FRENCH,
                Language.GERMAN, Language.ITALIAN, Language.PORTUGUESE,
                Language.DUTCH, Language.RUSSIAN, Language.JAPANESE,
                Language.CHINESE, Language.KOREAN, Language.ARABIC,
                Language.HINDI, Language.TURKISH, Language.POLISH,
            ]
            self.lingua_detector = LanguageDetectorBuilder.from_languages(*languages).build()
            logger.info("Lingua language detector initialized")
        except ImportError:
            logger.warning("lingua-language-detector not installed. Install with: pip install lingua-language-detector")

        try:
            # Initialize langdetect (confidence validator)
            import langdetect
            self.langdetect_ready = True
            logger.info("Langdetect initialized")
        except ImportError:
            logger.warning("langdetect not installed. Install with: pip install langdetect")

    async def detect_language(
        self,
        text: str,
        min_length: Optional[int] = None,
        preprocess: bool = True
    ) -> Tuple[str, float]:
        """
        Detect language of text using ensemble approach.

        Args:
            text: Text to detect language for
            min_length: Minimum text length (default: MIN_TEXT_LENGTH=10)
            preprocess: Whether to preprocess text first (default: True)

        Returns:
            Tuple of (language_code, confidence_score)
            where confidence_score is between 0.0 and 1.0

        Raises:
            ValueError: If text is empty or too short after preprocessing
            Exception: On detection failure when all methods fail
        """
        if min_length is None:
            min_length = self.MIN_TEXT_LENGTH

        # Preprocess text to remove noise
        if preprocess:
            cleaned_text = self.preprocess_text(text)
            logger.debug(f"Preprocessed: '{text[:50]}...' -> '{cleaned_text[:50]}...'")
        else:
            cleaned_text = text.strip()

        # Check minimum length after preprocessing
        if not cleaned_text or len(cleaned_text) < min_length:
            raise ValueError(
                f"Text must be at least {min_length} characters after preprocessing. "
                f"Got {len(cleaned_text)} chars: '{cleaned_text[:30]}...'"
            )

        # Initialize models if needed
        await self._initialize_models()

        # Run detection in executor to avoid blocking
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._detect_ensemble_sync,
            cleaned_text
        )
        return result

    def _detect_ensemble_sync(self, text: str) -> Tuple[str, float]:
        """
        Synchronous ensemble detection (runs in executor).

        Returns:
            Tuple of (language_code, confidence_score)
        """
        results = {}

        # 1. FastText detection (primary, fastest)
        fasttext_lang = None
        fasttext_conf = 0.0
        if self.fasttext_model:
            try:
                predictions = self.fasttext_model.predict(text, k=1)
                if predictions[0] and predictions[1]:
                    lang_code = predictions[0][0].replace('__label__', '')
                    confidence = predictions[1][0]
                    fasttext_lang = lang_code
                    fasttext_conf = confidence
                    results['fasttext'] = (lang_code, confidence)
                    logger.debug(f"FastText: {lang_code} ({confidence:.2%})")
            except Exception as e:
                logger.warning(f"FastText detection failed: {e}")

        # 2. Lingua detection (accuracy cross-check)
        lingua_lang = None
        lingua_conf = 0.0
        if self.lingua_detector:
            try:
                detection = self.lingua_detector.detect_language_of(text)
                if detection:
                    # Lingua 2.x uses iso_code_639_1 as an enum - convert to lowercase string
                    lang_code = detection.iso_code_639_1.name.lower()
                    # Lingua doesn't provide confidence, so estimate based on text length
                    lingua_conf = min(0.90, 0.70 + (len(text.split()) / 100))
                    lingua_lang = lang_code
                    results['lingua'] = (lang_code, lingua_conf)
                    logger.debug(f"Lingua: {lang_code} ({lingua_conf:.2%})")
            except Exception as e:
                logger.warning(f"Lingua detection failed: {e}")

        # 3. Langdetect detection (confidence validation)
        langdetect_lang = None
        langdetect_conf = 0.0
        if self.langdetect_ready:
            try:
                import langdetect
                # Suppress langdetect output
                langdetect.DetectorFactory.seed = 0
                lang_code = langdetect.detect(text)
                confidence = langdetect.detect_langs(text)[0].prob
                langdetect_lang = lang_code
                langdetect_conf = confidence
                results['langdetect'] = (lang_code, confidence)
                logger.debug(f"Langdetect: {lang_code} ({confidence:.2%})")
            except Exception as e:
                logger.warning(f"Langdetect detection failed: {e}")

        # Consensus logic
        if not results:
            raise Exception("All language detection methods failed")

        # Check agreement between detectors
        detected_langs = {lang for lang, _ in results.values()}

        if len(detected_langs) == 1:
            # All agree on same language - highest confidence
            lang_code = list(detected_langs)[0]
            confidence = 0.95
            logger.debug(f"All detectors agreed: {lang_code} (confidence=0.95)")
            return (lang_code, confidence)

        # Check if 2 out of 3 agree
        lang_votes = {}
        for detector_name, (lang, conf) in results.items():
            lang_votes.setdefault(lang, []).append((detector_name, conf))

        # Find language with most votes
        consensus_langs = {lang: votes for lang, votes in lang_votes.items() if len(votes) >= 2}

        if consensus_langs:
            # Find best consensus language (by highest average confidence)
            best_lang = max(
                consensus_langs.items(),
                key=lambda x: sum(conf for _, conf in x[1]) / len(x[1])
            )
            lang_code = best_lang[0]
            confidence = 0.90
            detectors = ', '.join(detector for detector, _ in best_lang[1])
            logger.debug(f"2 detectors agreed ({detectors}): {lang_code} (confidence=0.90)")
            return (lang_code, confidence)

        # No consensus - weighted decision based on detector reliability
        # Priority: Lingua > FastText > Langdetect (Lingua is most accurate for short text)

        # If langdetect has very high confidence (>85%), consider trusting it
        if langdetect_lang and langdetect_conf > 0.85:
            # But only if Lingua doesn't strongly disagree with high word count
            word_count = len(text.split())
            if lingua_lang and word_count >= 5 and lingua_lang != langdetect_lang:
                # Lingua is likely correct for longer text
                logger.debug(f"No consensus, preferring Lingua for {word_count} words: {lingua_lang} (confidence=0.80)")
                return (lingua_lang, 0.80)
            else:
                logger.debug(f"No consensus, using high-confidence Langdetect: {langdetect_lang} (confidence={langdetect_conf:.2f})")
                return (langdetect_lang, langdetect_conf * 0.9)  # Slight penalty for disagreement

        # Default priority: Lingua > FastText > Langdetect
        if lingua_lang:
            # Lingua is generally more accurate, especially for short texts
            logger.debug(f"No consensus, using Lingua (most accurate): {lingua_lang} (confidence=0.80)")
            return (lingua_lang, 0.80)
        elif fasttext_lang:
            logger.debug(f"No consensus, using FastText: {fasttext_lang} (confidence=0.75)")
            return (fasttext_lang, 0.75)
        elif langdetect_lang:
            logger.debug(f"No consensus, using Langdetect: {langdetect_lang} (confidence=0.70)")
            return (langdetect_lang, 0.70)
        else:
            raise Exception("No detector produced a result")

    async def health_check(self) -> bool:
        """
        Check if the ensemble detector is healthy.

        Returns:
            True if at least one detector is available
        """
        await self._initialize_models()

        available = []
        if self.fasttext_model:
            available.append('fasttext')
        if self.lingua_detector:
            available.append('lingua')
        if self.langdetect_ready:
            available.append('langdetect')

        logger.info(f"Ensemble detector health: {', '.join(available)}")
        return len(available) > 0


# Example usage for testing
if __name__ == '__main__':
    import asyncio

    async def test():
        detector = EnsembleLanguageDetector()

        test_texts = {
            'Hello, how are you?': 'en',
            '¿Hola, cómo estás?': 'es',
            'Bonjour, comment allez-vous?': 'fr',
            'Hola amigo, ¿cómo estás hoy?': 'es',
        }

        for text, expected_lang in test_texts.items():
            try:
                lang, confidence = await detector.detect_language(text)
                status = '✓' if lang == expected_lang else '✗'
                print(f"{status} {text[:30]:30} -> {lang} ({confidence:.2%})")
            except Exception as e:
                print(f"✗ {text[:30]:30} -> ERROR: {e}")

    asyncio.run(test())
