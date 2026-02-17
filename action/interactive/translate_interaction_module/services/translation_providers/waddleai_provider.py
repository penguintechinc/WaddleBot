"""
WaddleAI Translation Provider
=============================

Translation provider using the WaddleAI proxy for AI-powered translation.

Features:
- Uses WaddleAI's centralized AI proxy
- Fallback for advanced translation scenarios
- Language detection via AI
- Intelligent routing through WaddleAI
- Async HTTP client using httpx
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass, field

import httpx

from config import Config
from .base_provider import TranslationProvider, TranslationResult

logger = logging.getLogger(__name__)


@dataclass
class WaddleAITranslationConfig:
    """Configuration for WaddleAI translation provider."""
    base_url: str = field(default_factory=lambda: Config.WADDLEAI_BASE_URL)
    api_key: str = field(default_factory=lambda: Config.WADDLEAI_API_KEY)
    model: str = field(default_factory=lambda: Config.WADDLEAI_MODEL)
    temperature: float = field(
        default_factory=lambda: Config.WADDLEAI_TEMPERATURE
    )
    max_tokens: int = field(
        default_factory=lambda: Config.WADDLEAI_MAX_TOKENS
    )
    timeout: int = field(
        default_factory=lambda: Config.WADDLEAI_TIMEOUT
    )


class WaddleAIProvider(TranslationProvider):
    """
    AI-powered translation provider using WaddleAI proxy.

    This provider uses the WaddleAI centralized AI proxy for translations.
    It's intended as a fallback for complex translation scenarios or when
    higher quality translations are needed.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        timeout: Optional[int] = None
    ):
        """
        Initialize the WaddleAI translation provider.

        Args:
            base_url: WaddleAI base URL. Uses Config if None.
            api_key: WaddleAI API key. Uses Config if None.
            model: Model to use. Uses Config if None.
            temperature: Model temperature. Uses Config if None.
            max_tokens: Max tokens to generate. Uses Config if None.
            timeout: Request timeout in seconds. Uses Config if None.

        Raises:
            ValueError: If required config values are missing
        """
        super().__init__("waddleai")

        # Use provided values or fall back to config
        self.base_url = base_url or Config.WADDLEAI_BASE_URL
        self.api_key = api_key or Config.WADDLEAI_API_KEY
        self.model = model or Config.WADDLEAI_MODEL
        self.temperature = (
            temperature if temperature is not None
            else Config.WADDLEAI_TEMPERATURE
        )
        self.max_tokens = max_tokens or Config.WADDLEAI_MAX_TOKENS
        self.timeout = timeout or Config.WADDLEAI_TIMEOUT

        # Validate required config
        if not self.base_url:
            raise ValueError("WADDLEAI_BASE_URL not configured")
        if not self.api_key:
            raise ValueError("WADDLEAI_API_KEY not configured")
        if not self.model:
            raise ValueError("WADDLEAI_MODEL not configured")

        # Prepare headers
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        logger.info(
            f"Initialized WaddleAIProvider: {self.base_url} "
            f"(Model: {self.model})"
        )

    async def detect_language(
        self,
        text: str
    ) -> Tuple[str, float]:
        """
        Detect the language of the given text using WaddleAI.

        Uses an AI prompt to intelligently detect language.

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
            # Prepare AI request for language detection
            # Using Ollama native API format for direct Ollama integration
            prompt = f"""You are a language detection expert. Detect the language of the following text.
Return ONLY the ISO 639-1 language code (e.g., 'en', 'es', 'fr', 'de', 'ja', 'ko', 'zh', 'ru', 'ar') and your confidence (0.0-1.0).
Format: LANG_CODE:CONFIDENCE
Example: es:0.95

Text to analyze: "{text[:100]}"

Response (format LANG_CODE:CONFIDENCE only):"""

            # Detect if using Ollama directly (port 11434) or OpenAI-compatible proxy
            is_ollama_direct = ':11434' in self.base_url or 'ollama' in self.base_url.lower()

            async with httpx.AsyncClient() as client:
                if is_ollama_direct:
                    # Use Ollama native API
                    payload = {
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": self.temperature,
                            "num_predict": 20  # Short response
                        }
                    }
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json=payload,
                        timeout=self.timeout
                    )
                else:
                    # Use OpenAI-compatible API
                    messages = [
                        {"role": "system", "content": "You are a language detection expert."},
                        {"role": "user", "content": prompt}
                    ]
                    payload = {
                        "model": self.model,
                        "messages": messages,
                        "temperature": self.temperature,
                        "max_tokens": 20
                    }
                    response = await client.post(
                        f"{self.base_url}/v1/chat/completions",
                        headers=self.headers,
                        json=payload,
                        timeout=self.timeout
                    )

                if response.status_code == 200:
                    data = response.json()
                    # Handle both Ollama and OpenAI response formats
                    if is_ollama_direct:
                        content = data.get('response', '').strip()
                    else:
                        content = data['choices'][0]['message']['content'].strip()

                    # Parse response (format: LANG_CODE:CONFIDENCE)
                    # Handle variations like "en:0.95", "en: 0.95", "English (en):0.95"
                    parts = content.split(':')
                    if len(parts) >= 2:
                        # Extract language code (take first 2-3 lowercase letters)
                        lang_part = parts[0].strip().lower()
                        # Remove any parentheses content
                        if '(' in lang_part:
                            lang_part = lang_part.split('(')[0].strip()
                        # Take only the first 2-3 chars that look like a language code
                        lang_code = ''.join(c for c in lang_part if c.isalpha())[:3]
                        if len(lang_code) < 2:
                            lang_code = lang_part[:2]

                        try:
                            # Extract confidence (first number-like part)
                            conf_part = parts[1].strip()
                            # Remove any trailing text after the number
                            conf_str = ''.join(c for c in conf_part[:5] if c.isdigit() or c == '.')
                            confidence = float(conf_str) if conf_str else 0.8
                            confidence = min(1.0, max(0.0, confidence))
                        except (ValueError, IndexError):
                            confidence = 0.8

                        logger.debug(
                            f"WaddleAI detected language: {lang_code} "
                            f"(confidence: {confidence:.2f})"
                        )
                        return (lang_code, confidence)

                    # Fallback if parsing fails - try to extract just language code
                    lang_code = ''.join(c for c in content.lower() if c.isalpha())[:2]
                    if lang_code:
                        logger.warning(f"Partial parse of language detection: {content} -> {lang_code}")
                        return (lang_code, 0.7)

                    logger.warning(f"Failed to parse language detection: {content}")
                    return ("unknown", 0.5)

                elif response.status_code == 401:
                    logger.error("WaddleAI authentication failed")
                    raise Exception("WaddleAI authentication failed")

                elif response.status_code == 429:
                    logger.error("WaddleAI rate limit exceeded")
                    raise Exception("WaddleAI rate limit exceeded")

                else:
                    logger.error(
                        f"WaddleAI error: {response.status_code} - {response.text}"
                    )
                    raise Exception(
                        f"WaddleAI error: {response.status_code}"
                    )

        except httpx.TimeoutException:
            logger.error(f"WaddleAI request timed out after {self.timeout}s")
            raise

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
        Translate text using WaddleAI.

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

            # Prepare AI request for translation
            system_prompt = (
                f"You are a professional translator. "
                f"Translate the following text from {source_lang} to {target_lang}. "
                f"Return ONLY the translation, nothing else."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    translated_text = (
                        data['choices'][0]['message']['content'].strip()
                    )

                    logger.info(
                        f"Translated {source_lang} -> {target_lang} via WaddleAI: "
                        f"'{text[:50]}...' -> '{translated_text[:50]}...'"
                    )

                    return TranslationResult(
                        original_text=text,
                        translated_text=translated_text,
                        detected_lang=source_lang,
                        target_lang=target_lang,
                        confidence=0.8,  # Assumed confidence for AI
                        provider=self.provider_name,
                        cached=False
                    )

                elif response.status_code == 401:
                    logger.error("WaddleAI authentication failed")
                    raise Exception("WaddleAI authentication failed")

                elif response.status_code == 429:
                    logger.error("WaddleAI rate limit exceeded")
                    raise Exception("WaddleAI rate limit exceeded")

                else:
                    logger.error(
                        f"WaddleAI error: {response.status_code} - {response.text}"
                    )
                    raise Exception(
                        f"WaddleAI error: {response.status_code}"
                    )

        except httpx.TimeoutException:
            logger.error(f"WaddleAI request timed out after {self.timeout}s")
            raise

        except Exception as e:
            logger.error(
                f"Translation failed: {e}",
                exc_info=True
            )
            raise

    async def health_check(self) -> bool:
        """
        Check if WaddleAI is accessible.

        This performs a test request to the WaddleAI health endpoint.

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/healthz",
                    headers=self.headers,
                    timeout=5.0
                )

                is_healthy = response.status_code == 200

                if is_healthy:
                    logger.debug("WaddleAIProvider health check passed")
                else:
                    logger.warning(
                        f"WaddleAIProvider health check returned "
                        f"status {response.status_code}"
                    )

                return is_healthy

        except Exception as e:
            logger.error(
                f"WaddleAIProvider health check failed: {e}",
                exc_info=True
            )
            return False

    async def should_translate_pattern(
        self,
        pattern: str,
        context: str,
        platform: str
    ) -> Tuple[bool, float]:
        """
        Ask AI whether an uncertain pattern should be translated.

        Used for patterns that might be emotes, slang, or memes that
        should not be translated.

        Args:
            pattern: The uncertain pattern (e.g., 'Pog', 'monkaS', 'KEKW')
            context: Surrounding message context
            platform: Platform name for context (twitch, discord, etc.)

        Returns:
            Tuple of (should_translate: bool, confidence: float)
            - should_translate: True if pattern should be translated
            - confidence: AI's confidence in the decision (0.0-1.0)

        Example:
            >>> should_translate, conf = await provider.should_translate_pattern(
            ...     "monkaS", "I'm feeling monkaS about this", "twitch"
            ... )
            >>> print(should_translate, conf)
            False, 0.92  # It's a Twitch emote, don't translate
        """
        if not pattern or not pattern.strip():
            # Empty pattern, skip translation
            return False, 1.0

        try:
            # Build AI prompt for translation decision
            system_prompt = """You are an expert in chat platform terminology, gaming slang, and internet culture.

Determine if the following word/phrase should be TRANSLATED or PRESERVED as-is.

PRESERVE (answer NO) if it's:
- A platform emote or custom emote (e.g., Kappa, PogChamp, monkaS, KEKW, LUL)
- Internet/gaming slang specific to streaming (e.g., Pog, W, L, gg, copium)
- A meme or catchphrase that loses meaning when translated
- A username or nickname reference
- An acronym commonly used in chat (e.g., POV, LMAO, GG)

TRANSLATE (answer YES) if it's:
- A regular word in a foreign language that should be translated
- A phrase that has clear meaning in the target language
- Normal vocabulary that isn't platform-specific

Respond with ONLY: YES:confidence or NO:confidence
Where confidence is 0.0 to 1.0

Examples:
- "Kappa" on twitch -> NO:0.95 (Twitch emote)
- "monkaS" on twitch -> NO:0.92 (BTTV/7TV emote)
- "Hola" to English -> YES:0.90 (Spanish word, should translate)
- "KEKW" on any platform -> NO:0.88 (common emote)
- "bonjour" to English -> YES:0.95 (French word, should translate)
"""

            user_prompt = f"""Platform: {platform}
Pattern to evaluate: "{pattern}"
Message context: "{context[:100] if context else 'N/A'}"

Should this pattern be translated? Answer YES:confidence or NO:confidence"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,  # Lower temperature for more consistent decisions
                "max_tokens": 20  # Very short response needed
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=min(self.timeout, 5)  # Cap at 5 seconds for decisions
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data['choices'][0]['message']['content'].strip().upper()

                    # Parse response (format: YES:0.95 or NO:0.85)
                    should_translate = True  # Default to translate if parsing fails
                    confidence = 0.5

                    if ':' in content:
                        parts = content.split(':')
                        answer = parts[0].strip()
                        should_translate = answer.startswith('YES')

                        try:
                            confidence = float(parts[1].strip())
                            confidence = min(1.0, max(0.0, confidence))
                        except (ValueError, IndexError):
                            confidence = 0.7

                    elif content.startswith('YES'):
                        should_translate = True
                        confidence = 0.7
                    elif content.startswith('NO'):
                        should_translate = False
                        confidence = 0.7

                    logger.debug(
                        f"AI decision for '{pattern}': "
                        f"{'translate' if should_translate else 'preserve'} "
                        f"(confidence: {confidence:.2f})"
                    )

                    return should_translate, confidence

                else:
                    logger.warning(
                        f"AI decision request failed: {response.status_code}"
                    )
                    # Default: preserve uncertain patterns (don't translate)
                    return False, 0.5

        except httpx.TimeoutException:
            logger.warning(f"AI decision timed out for pattern '{pattern}'")
            # On timeout, preserve the pattern (safer not to translate)
            return False, 0.5

        except Exception as e:
            logger.error(f"AI decision failed for '{pattern}': {e}")
            # On error, preserve the pattern (safer not to translate)
            return False, 0.5
