"""
Translation Preprocessor - Token Detection and Placeholder Management
=====================================================================

Handles detection and preservation of tokens that should NOT be translated:
- @mentions (usernames)
- !commands and #commands
- Email addresses
- URLs
- Platform-specific emotes (Twitch, Discord, Slack, Kick)

Uses placeholder tokens during translation, then restores originals after.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class TokenType(Enum):
    """Types of tokens to preserve during translation."""
    MENTION = "mention"           # @username
    COMMAND = "command"           # !command or #command
    EMAIL = "email"               # user@example.com
    URL = "url"                   # http/https URLs
    EMOTE = "emote"               # Platform-specific emotes
    UNCERTAIN = "uncertain"       # Unknown patterns needing AI decision


@dataclass
class PreservedToken:
    """Represents a token preserved from translation."""
    token_type: TokenType
    original_text: str
    placeholder: str
    start_pos: int
    end_pos: int
    metadata: Dict = field(default_factory=dict)


@dataclass
class PreprocessResult:
    """Result of text preprocessing."""
    processed_text: str
    tokens: List[PreservedToken]
    uncertain_patterns: List[str]
    needs_ai_decision: bool
    original_text: str


# =============================================================================
# REGEX PATTERNS
# =============================================================================

# @username mentions (alphanumeric + underscore, 1-25 chars typical)
MENTION_PATTERN = re.compile(r'@[\w]{1,25}', re.UNICODE)

# !command or #command at word boundary
COMMAND_PATTERN = re.compile(r'(?:^|(?<=\s))[!#][\w]+', re.UNICODE)

# Email addresses (RFC 5322 simplified)
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.UNICODE
)

# URLs (http/https)
URL_PATTERN = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+',
    re.UNICODE
)

# Discord custom emotes: <:name:id> or <a:name:id> (animated)
DISCORD_EMOTE_PATTERN = re.compile(r'<a?:[\w]+:\d+>')

# Slack emotes: :emoji_name:
SLACK_EMOTE_PATTERN = re.compile(r':[\w+-]+:')

# Potential emotes for uncertain detection:
# - CamelCase words (e.g., PogChamp, Kappa, LUL)
# - ALL_CAPS words 2+ chars that might be emotes
POTENTIAL_EMOTE_PATTERN = re.compile(
    r'\b(?:[A-Z][a-z]+(?:[A-Z][a-z]*)+|[A-Z]{2,}[a-z]*)\b'
)

# Common emote suffixes/prefixes (case-insensitive matching)
EMOTE_SUFFIXES = {'champ', 'w', 's', 'ge', 'gasm', 'hands', 'time', 'man', 'guy', 'face', 'eyes'}
EMOTE_PREFIXES = {'pog', 'pepe', 'feels', 'monka', 'kek', 'omg', 'lul', 'kappa', 'peepo', 'ez', 'hype'}

# Known emote fragments that strongly indicate an emote
EMOTE_FRAGMENTS = {
    'pog', 'kappa', 'lul', 'kek', 'pepe', 'monka', 'feels', 'copium', 'hopium',
    'sadge', 'madge', 'bedge', 'nodders', 'pepega', 'wicked', 'based', 'cringe',
    'gigachad', 'copege', 'aware', 'clueless', 'susge', 'modcheck', 'oooo',
    'catjam', 'jammies', 'blobdance', 'peepohappy', 'peeposad', 'widepeepo',
    'omegalul', 'lulw', 'kekw', 'icant', 'diesofcringe', 'skull', 'nerd',
}

# Common English words that should NOT be treated as emotes (lowercase)
# These are words that might match CamelCase or CAPS patterns but are normal words
COMMON_WORDS_WHITELIST = {
    # Common acronyms
    'usa', 'uk', 'eu', 'us', 'id', 'tv', 'pc', 'ok', 'dj', 'vs', 'hr', 'pr',
    'ceo', 'cto', 'cfo', 'vp', 'pm', 'am', 'gm', 'gg', 'wp', 'gl', 'hf',
    # Common CamelCase words (brands, tech)
    'youtube', 'twitch', 'discord', 'spotify', 'netflix', 'amazon', 'google',
    'facebook', 'instagram', 'twitter', 'tiktok', 'snapchat', 'whatsapp',
    'iphone', 'ipad', 'ipod', 'imac', 'ios', 'macos', 'windows', 'linux',
    'javascript', 'typescript', 'python', 'minecraft', 'fortnite', 'valorant',
    'playstation', 'xbox', 'nintendo', 'pokemon', 'digimon',
    # Common words that might be caps
    'lol', 'rofl', 'lmao', 'omg', 'wtf', 'brb', 'afk', 'imo', 'idk', 'tbh',
    'fyi', 'asap', 'rip', 'irl', 'lfg', 'ftw', 'goat', 'goated',
    # Names and places
    'john', 'mike', 'david', 'chris', 'alex', 'max', 'sam', 'tom', 'bob',
}


class TranslationPreprocessor:
    """
    Handles token detection and placeholder management for translation.

    Detects tokens that should be preserved during translation, replaces
    them with placeholders, and restores them after translation completes.
    """

    # Placeholder format: {{TYPE_INDEX}}
    # Using double curly braces which translation APIs typically preserve
    PLACEHOLDER_PREFIXES = {
        TokenType.MENTION: "M",
        TokenType.COMMAND: "C",
        TokenType.EMAIL: "L",  # L for 'mail' to avoid E conflict
        TokenType.URL: "U",
        TokenType.EMOTE: "E",
        TokenType.UNCERTAIN: "X",
    }

    def __init__(
        self,
        emote_service: Optional['EmoteService'] = None,
        ai_decision_service: Optional['AIDecisionService'] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize the preprocessor.

        Args:
            emote_service: Service for checking platform emotes
            ai_decision_service: Service for AI-based translation decisions
            config: Preprocessing configuration
        """
        self.emote_service = emote_service
        self.ai_decision_service = ai_decision_service
        self.config = config or self._default_config()

        logger.info("TranslationPreprocessor initialized")

    def _default_config(self) -> Dict:
        """Return default preprocessing configuration."""
        return {
            "enabled": True,
            "preserve_mentions": True,
            "preserve_commands": True,
            "preserve_emails": True,
            "preserve_urls": True,
            "preserve_emotes": True,
            "detect_uncertain": True,
        }

    async def preprocess(
        self,
        text: str,
        platform: str,
        channel_id: Optional[str] = None,
        config: Optional[Dict] = None
    ) -> PreprocessResult:
        """
        Preprocess text by replacing tokens with placeholders.

        Args:
            text: Original message text
            platform: Platform name (twitch, discord, slack, kick)
            channel_id: Channel ID for channel-specific emotes
            config: Optional preprocessing config override

        Returns:
            PreprocessResult with processed text and token list
        """
        cfg = config or self.config

        if not cfg.get("enabled", True):
            return PreprocessResult(
                processed_text=text,
                tokens=[],
                uncertain_patterns=[],
                needs_ai_decision=False,
                original_text=text
            )

        tokens: List[PreservedToken] = []
        uncertain_patterns: List[str] = []

        # Collect all token matches with their positions
        # Order matters: process in order of specificity

        # 1. URLs first (they may contain @ or other patterns)
        if cfg.get("preserve_urls", True):
            url_matches = self._detect_urls(text)
            tokens.extend(url_matches)

        # 2. Emails (before mentions, as emails contain @)
        if cfg.get("preserve_emails", True):
            email_matches = self._detect_emails(text, tokens)
            tokens.extend(email_matches)

        # 3. Mentions
        if cfg.get("preserve_mentions", True):
            mention_matches = self._detect_mentions(text, tokens)
            tokens.extend(mention_matches)

        # 4. Commands
        if cfg.get("preserve_commands", True):
            command_matches = self._detect_commands(text, tokens)
            tokens.extend(command_matches)

        # 5. Platform-specific emotes
        if cfg.get("preserve_emotes", True):
            emote_matches, uncertain = await self._detect_emotes(
                text, platform, channel_id, tokens
            )
            tokens.extend(emote_matches)
            uncertain_patterns.extend(uncertain)

        # Sort tokens by position (start_pos) for proper replacement
        tokens.sort(key=lambda t: t.start_pos)

        # Assign placeholders to tokens
        self._assign_placeholders(tokens)

        # Replace tokens with placeholders (reverse order to preserve positions)
        processed_text = self._replace_with_placeholders(text, tokens)

        needs_ai = bool(uncertain_patterns) and cfg.get("detect_uncertain", True)

        logger.debug(
            f"Preprocessed text: {len(tokens)} tokens preserved, "
            f"{len(uncertain_patterns)} uncertain patterns"
        )

        return PreprocessResult(
            processed_text=processed_text,
            tokens=tokens,
            uncertain_patterns=uncertain_patterns,
            needs_ai_decision=needs_ai,
            original_text=text
        )

    def postprocess(
        self,
        translated_text: str,
        tokens: List[PreservedToken]
    ) -> str:
        """
        Restore original tokens from placeholders after translation.

        Args:
            translated_text: Text after translation
            tokens: List of preserved tokens from preprocessing

        Returns:
            Final text with tokens restored
        """
        if not tokens:
            return translated_text

        result = translated_text

        # Replace placeholders with original tokens
        for token in tokens:
            if token.placeholder in result:
                result = result.replace(token.placeholder, token.original_text)
            else:
                # Placeholder may have been mangled by translation
                # Try common variations
                variations = self._get_placeholder_variations(token.placeholder)
                for variation in variations:
                    if variation in result:
                        result = result.replace(variation, token.original_text)
                        logger.debug(
                            f"Restored token using variation: {variation} -> {token.original_text}"
                        )
                        break
                else:
                    logger.warning(
                        f"Placeholder not found in translation: {token.placeholder}"
                    )

        return result

    def _detect_urls(self, text: str) -> List[PreservedToken]:
        """Detect URLs in text."""
        tokens = []
        for match in URL_PATTERN.finditer(text):
            tokens.append(PreservedToken(
                token_type=TokenType.URL,
                original_text=match.group(),
                placeholder="",  # Assigned later
                start_pos=match.start(),
                end_pos=match.end()
            ))
        return tokens

    def _detect_emails(
        self,
        text: str,
        existing_tokens: List[PreservedToken]
    ) -> List[PreservedToken]:
        """Detect email addresses, avoiding overlap with existing tokens."""
        tokens = []
        for match in EMAIL_PATTERN.finditer(text):
            if not self._overlaps_existing(match.start(), match.end(), existing_tokens):
                tokens.append(PreservedToken(
                    token_type=TokenType.EMAIL,
                    original_text=match.group(),
                    placeholder="",
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        return tokens

    def _detect_mentions(
        self,
        text: str,
        existing_tokens: List[PreservedToken]
    ) -> List[PreservedToken]:
        """Detect @username mentions, avoiding overlap with emails/URLs."""
        tokens = []
        for match in MENTION_PATTERN.finditer(text):
            if not self._overlaps_existing(match.start(), match.end(), existing_tokens):
                tokens.append(PreservedToken(
                    token_type=TokenType.MENTION,
                    original_text=match.group(),
                    placeholder="",
                    start_pos=match.start(),
                    end_pos=match.end()
                ))
        return tokens

    def _detect_commands(
        self,
        text: str,
        existing_tokens: List[PreservedToken]
    ) -> List[PreservedToken]:
        """Detect !command and #command patterns."""
        tokens = []
        for match in COMMAND_PATTERN.finditer(text):
            cmd_text = match.group().strip()  # Remove leading whitespace from match
            start = text.find(cmd_text, match.start())
            if not self._overlaps_existing(start, start + len(cmd_text), existing_tokens):
                tokens.append(PreservedToken(
                    token_type=TokenType.COMMAND,
                    original_text=cmd_text,
                    placeholder="",
                    start_pos=start,
                    end_pos=start + len(cmd_text)
                ))
        return tokens

    async def _detect_emotes(
        self,
        text: str,
        platform: str,
        channel_id: Optional[str],
        existing_tokens: List[PreservedToken]
    ) -> Tuple[List[PreservedToken], List[str]]:
        """
        Detect platform-specific emotes with confidence scoring.

        Uses multiple signals to determine if a word is likely an emote:
        - Known emote cache (BTTV/FFZ/7TV)
        - Pattern matching (CamelCase, CAPS)
        - Emote fragments/prefixes/suffixes
        - Common word whitelist
        - Message position context

        Errs on the side of NOT translating - better to skip than mangle.

        Returns:
            Tuple of (detected emote tokens, uncertain patterns)
        """
        tokens = []
        uncertain = []

        # Platform-specific patterns (these are definite matches)
        if platform == "discord":
            # Discord custom emotes: <:name:id>
            for match in DISCORD_EMOTE_PATTERN.finditer(text):
                if not self._overlaps_existing(match.start(), match.end(), existing_tokens):
                    tokens.append(PreservedToken(
                        token_type=TokenType.EMOTE,
                        original_text=match.group(),
                        placeholder="",
                        start_pos=match.start(),
                        end_pos=match.end(),
                        metadata={"source": "discord_native", "confidence": 1.0}
                    ))

        elif platform == "slack":
            # Slack emotes: :emoji:
            for match in SLACK_EMOTE_PATTERN.finditer(text):
                if not self._overlaps_existing(match.start(), match.end(), existing_tokens):
                    tokens.append(PreservedToken(
                        token_type=TokenType.EMOTE,
                        original_text=match.group(),
                        placeholder="",
                        start_pos=match.start(),
                        end_pos=match.end(),
                        metadata={"source": "slack_native", "confidence": 1.0}
                    ))

        # Get known emotes for this platform/channel
        known_emotes: Set[str] = set()
        if self.emote_service:
            known_emotes = await self.emote_service.get_emotes(platform, channel_id)

        # Find words that might be emotes
        words = text.split()
        word_count = len(words)

        current_pos = 0
        for word_idx, word in enumerate(words):
            word_start = text.find(word, current_pos)
            word_end = word_start + len(word)
            current_pos = word_end

            # Skip if already matched
            if self._overlaps_existing(word_start, word_end, existing_tokens + tokens):
                continue

            # Clean the word (strip punctuation)
            clean_word = word.strip('.,!?;:\'\"')
            if not clean_word:
                continue

            # Check if word is a known emote (definite match)
            if clean_word in known_emotes:
                tokens.append(PreservedToken(
                    token_type=TokenType.EMOTE,
                    original_text=clean_word,
                    placeholder="",
                    start_pos=word_start,
                    end_pos=word_start + len(clean_word),
                    metadata={"source": "emote_service", "confidence": 1.0}
                ))
                continue

            # Calculate emote confidence score
            confidence = self._calculate_emote_confidence(
                clean_word, platform, word_idx, word_count
            )

            # High confidence (>= 0.7): Treat as emote, preserve without AI
            # Medium confidence (0.4-0.7): Mark as uncertain, may ask AI
            # Low confidence (< 0.4): Probably not an emote, translate normally

            if confidence >= 0.7:
                # High confidence - treat as emote
                tokens.append(PreservedToken(
                    token_type=TokenType.EMOTE,
                    original_text=clean_word,
                    placeholder="",
                    start_pos=word_start,
                    end_pos=word_start + len(clean_word),
                    metadata={"source": "heuristic", "confidence": confidence}
                ))
                logger.debug(f"High confidence emote: '{clean_word}' ({confidence:.2f})")

            elif confidence >= 0.4:
                # Medium confidence - mark as uncertain for potential AI check
                uncertain.append(clean_word)
                logger.debug(f"Uncertain pattern: '{clean_word}' ({confidence:.2f})")

            # Low confidence - let it be translated

        return tokens, uncertain

    def _calculate_emote_confidence(
        self,
        word: str,
        platform: str,
        word_idx: int,
        word_count: int
    ) -> float:
        """
        Calculate confidence score that a word is an emote.

        Scoring signals:
        - Contains known emote fragment: +0.4
        - Has emote prefix/suffix: +0.3
        - CamelCase or ALL_CAPS pattern: +0.2
        - Position at end of message: +0.1
        - Twitch platform bonus: +0.1
        - In common words whitelist: -0.5
        - Very short (1-2 chars): -0.3

        Returns:
            Confidence score between 0.0 and 1.0
        """
        score = 0.0
        word_lower = word.lower()

        # Negative signals first (early exit if clearly not an emote)

        # Common word whitelist - definitely not an emote
        if word_lower in COMMON_WORDS_WHITELIST:
            return 0.0

        # Very short words are rarely emotes (except specific ones)
        if len(word) <= 2:
            score -= 0.3

        # Positive signals

        # Contains known emote fragment (strong signal)
        for fragment in EMOTE_FRAGMENTS:
            if fragment in word_lower:
                score += 0.5
                break

        # Has emote-like prefix
        for prefix in EMOTE_PREFIXES:
            if word_lower.startswith(prefix):
                score += 0.3
                break

        # Has emote-like suffix
        for suffix in EMOTE_SUFFIXES:
            if word_lower.endswith(suffix):
                score += 0.25
                break

        # CamelCase pattern (PogChamp, FeelsBadMan)
        if re.match(r'^[A-Z][a-z]+(?:[A-Z][a-z]*)+$', word):
            score += 0.25

        # ALL_CAPS pattern (KEKW, LUL, OMEGALUL)
        elif re.match(r'^[A-Z]{2,}[a-z]*$', word):
            score += 0.2

        # Ends with W (very common emote pattern: KEKW, LULW, PogW)
        if word_lower.endswith('w') and len(word) >= 3:
            score += 0.15

        # Position context: emotes often appear at end of message
        if word_count > 1 and word_idx >= word_count - 2:
            score += 0.1

        # Platform bonus: Twitch has more emotes
        if platform == "twitch":
            score += 0.1

        # Standalone word (not part of sentence structure)
        if word_count == 1:
            score += 0.1

        # Cap at 1.0
        return min(1.0, max(0.0, score))

    def _overlaps_existing(
        self,
        start: int,
        end: int,
        existing: List[PreservedToken]
    ) -> bool:
        """Check if a position range overlaps with any existing token."""
        for token in existing:
            if not (end <= token.start_pos or start >= token.end_pos):
                return True
        return False

    def _assign_placeholders(self, tokens: List[PreservedToken]) -> None:
        """Assign unique placeholders to each token."""
        counters: Dict[TokenType, int] = {}

        for token in tokens:
            token_type = token.token_type
            index = counters.get(token_type, 0)
            prefix = self.PLACEHOLDER_PREFIXES[token_type]
            token.placeholder = f"{{{{{prefix}{index}}}}}"
            counters[token_type] = index + 1

    def _replace_with_placeholders(
        self,
        text: str,
        tokens: List[PreservedToken]
    ) -> str:
        """Replace tokens with their placeholders."""
        if not tokens:
            return text

        # Process in reverse order to preserve positions
        result = text
        for token in reversed(tokens):
            result = (
                result[:token.start_pos] +
                token.placeholder +
                result[token.end_pos:]
            )

        return result

    def _get_placeholder_variations(self, placeholder: str) -> List[str]:
        """
        Generate variations of a placeholder that might occur after translation.

        Some translation APIs may alter the placeholder format.
        """
        # Original: {{M0}}
        variations = [
            placeholder,
            placeholder.replace("{{", "{").replace("}}", "}"),  # {M0}
            placeholder.replace("{{", "{ {").replace("}}", "} }"),  # { {M0} }
            placeholder.replace("{{", "[[").replace("}}", "]]"),  # [[M0]]
            placeholder.lower(),  # {{m0}}
            placeholder.upper(),  # {{M0}} (already uppercase, but just in case)
        ]

        # Also try with spaces
        inner = placeholder[2:-2]  # Extract M0 from {{M0}}
        variations.extend([
            f"{{ {inner} }}",
            f"[ {inner} ]",
            f"( {inner} )",
        ])

        return variations


class AIDecisionService:
    """
    Service for asking AI whether uncertain patterns should be translated.

    Used when the preprocessor encounters patterns that might be emotes
    or slang but aren't in the known emote cache.
    """

    def __init__(self, waddleai_provider, cache_manager, dal):
        """
        Initialize AI decision service.

        Args:
            waddleai_provider: WaddleAI provider for AI calls
            cache_manager: Redis cache manager
            dal: Database access layer
        """
        self.provider = waddleai_provider
        self.cache = cache_manager
        self.dal = dal

    async def should_translate_pattern(
        self,
        pattern: str,
        context: str,
        platform: str,
        config: Optional[Dict] = None
    ) -> Tuple[bool, float]:
        """
        Ask AI whether a pattern should be translated.

        Args:
            pattern: The uncertain pattern (e.g., 'Pog', 'monkaS')
            context: Surrounding message context
            platform: Platform name for context

        Returns:
            Tuple of (should_translate: bool, confidence: float)
        """
        # Check cache first
        cache_key = self._get_cache_key(pattern, platform)
        cached = await self._get_cached_decision(cache_key, platform)
        if cached is not None:
            return cached

        # Ask AI
        try:
            should_translate, confidence = await self._ask_ai(
                pattern, context, platform
            )

            # Cache the decision
            await self._cache_decision(
                cache_key, pattern, platform, should_translate, confidence
            )

            return should_translate, confidence

        except Exception as e:
            logger.error(f"AI decision failed for pattern '{pattern}': {e}")
            # Default: preserve the pattern (don't translate)
            return False, 0.5

    def _get_cache_key(self, pattern: str, platform: str) -> str:
        """Generate cache key for AI decision."""
        key_material = f"{platform}:{pattern.lower()}"
        return hashlib.sha256(key_material.encode()).hexdigest()

    async def _get_cached_decision(
        self,
        cache_key: str,
        platform: str
    ) -> Optional[Tuple[bool, float]]:
        """Check cache for existing decision."""
        # Try Redis first
        redis_key = f"ai_decision:{cache_key}"
        cached = await self.cache.get(redis_key)
        if cached:
            try:
                parts = cached.split(':')
                return parts[0] == 'true', float(parts[1])
            except (ValueError, IndexError):
                pass

        # Try database
        try:
            result = self.dal.executesql(
                "SELECT * FROM get_cached_ai_decision(%s, %s)",
                [cache_key, platform]
            )
            if result and len(result) > 0:
                row = result[0]
                return bool(row[0]), float(row[1])
        except Exception as e:
            logger.warning(f"DB cache lookup failed: {e}")

        return None

    async def _ask_ai(
        self,
        pattern: str,
        context: str,
        platform: str
    ) -> Tuple[bool, float]:
        """Call AI to make translation decision."""
        # This will be implemented by calling waddleai_provider
        # with a specialized prompt
        result = await self.provider.should_translate_pattern(
            pattern, context, platform
        )
        return result

    async def _cache_decision(
        self,
        cache_key: str,
        pattern: str,
        platform: str,
        should_translate: bool,
        confidence: float
    ) -> None:
        """Cache AI decision in Redis and database."""
        # Redis cache (1 hour)
        redis_key = f"ai_decision:{cache_key}"
        value = f"{'true' if should_translate else 'false'}:{confidence:.2f}"
        await self.cache.set(redis_key, value, ttl=3600)

        # Database cache
        try:
            self.dal.executesql(
                """
                INSERT INTO ai_translation_decision_cache
                (pattern_hash, pattern, platform, should_translate, confidence, expires_at)
                VALUES (%s, %s, %s, %s, %s, NOW() + INTERVAL '1 hour')
                ON CONFLICT (pattern_hash, platform)
                DO UPDATE SET
                    should_translate = EXCLUDED.should_translate,
                    confidence = EXCLUDED.confidence,
                    expires_at = NOW() + INTERVAL '1 hour',
                    access_count = ai_translation_decision_cache.access_count + 1
                """,
                [cache_key, pattern, platform, should_translate, confidence]
            )
            self.dal.commit()
        except Exception as e:
            logger.warning(f"Failed to cache AI decision in DB: {e}")
