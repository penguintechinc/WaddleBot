"""
Slack Emote Provider - Regex-based Slack emoji detection
=========================================================

Slack emotes use the format :emoji_name:
This provider detects these patterns via regex.

Slack also has custom workspace emotes, but those would require
Slack API access with workspace tokens.
"""

import logging
import re
from typing import List, Optional, Set

from .base_emote_provider import BaseEmoteProvider, Emote

logger = logging.getLogger(__name__)

# Slack emoji pattern: :emoji_name: (alphanumeric, underscore, hyphen, plus)
SLACK_EMOTE_PATTERN = re.compile(r':[\w+-]+:')

# Common Slack/standard emoji names (subset for quick matching)
# Full list would be extensive - these are most common
COMMON_SLACK_EMOJI: Set[str] = {
    # Faces
    ':smile:', ':grinning:', ':joy:', ':rofl:', ':smiley:', ':grin:',
    ':sweat_smile:', ':laughing:', ':wink:', ':blush:', ':yum:',
    ':sunglasses:', ':heart_eyes:', ':kissing_heart:', ':relaxed:',
    ':stuck_out_tongue:', ':stuck_out_tongue_winking_eye:',
    ':stuck_out_tongue_closed_eyes:', ':disappointed:', ':worried:',
    ':angry:', ':rage:', ':cry:', ':sob:', ':fearful:', ':weary:',
    ':sleepy:', ':tired_face:', ':grimacing:', ':thinking_face:',
    ':face_with_raised_eyebrow:', ':neutral_face:', ':expressionless:',
    ':no_mouth:', ':face_with_rolling_eyes:', ':smirk:', ':persevere:',
    ':disappointed_relieved:', ':open_mouth:', ':zipper_mouth_face:',
    ':hushed:', ':sleeping:', ':drooling_face:', ':lying_face:',
    ':nerd_face:', ':flushed:', ':scream:', ':astonished:',
    ':cold_sweat:', ':skull:', ':ghost:', ':alien:', ':robot_face:',

    # Hands
    ':thumbsup:', ':thumbsdown:', ':+1:', ':-1:', ':ok_hand:', ':wave:',
    ':raised_hands:', ':clap:', ':pray:', ':handshake:', ':point_up:',
    ':point_down:', ':point_left:', ':point_right:', ':middle_finger:',
    ':raised_hand:', ':vulcan_salute:', ':metal:', ':call_me_hand:',
    ':muscle:', ':writing_hand:', ':selfie:',

    # Hearts
    ':heart:', ':yellow_heart:', ':green_heart:', ':blue_heart:',
    ':purple_heart:', ':black_heart:', ':broken_heart:', ':heartbeat:',
    ':heartpulse:', ':sparkling_heart:', ':cupid:', ':gift_heart:',
    ':revolving_hearts:', ':heart_decoration:', ':heavy_heart_exclamation:',

    # Common reactions
    ':fire:', ':100:', ':tada:', ':sparkles:', ':star:', ':star2:',
    ':boom:', ':collision:', ':zap:', ':sunny:', ':cloud:', ':umbrella:',
    ':snowflake:', ':rainbow:', ':ocean:', ':rocket:', ':airplane:',
    ':car:', ':bike:', ':house:', ':office:', ':hospital:',

    # Objects
    ':coffee:', ':beer:', ':beers:', ':wine_glass:', ':cocktail:',
    ':pizza:', ':hamburger:', ':fries:', ':popcorn:', ':cake:',
    ':cookie:', ':doughnut:', ':ice_cream:', ':birthday:', ':gift:',
    ':balloon:', ':confetti_ball:', ':trophy:', ':medal:', ':crown:',
    ':gem:', ':moneybag:', ':dollar:', ':credit_card:', ':computer:',
    ':keyboard:', ':desktop_computer:', ':phone:', ':camera:',
    ':video_camera:', ':movie_camera:', ':tv:', ':radio:', ':microphone:',
    ':headphones:', ':musical_note:', ':notes:', ':guitar:', ':trumpet:',
    ':violin:', ':drum:', ':bell:', ':loudspeaker:', ':mega:', ':mailbox:',
    ':envelope:', ':email:', ':inbox_tray:', ':outbox_tray:', ':package:',
    ':clipboard:', ':pushpin:', ':paperclip:', ':scissors:', ':lock:',
    ':key:', ':hammer:', ':wrench:', ':gear:', ':bulb:', ':flashlight:',
    ':mag:', ':microscope:', ':telescope:', ':satellite:', ':syringe:',
    ':pill:', ':door:', ':bed:', ':toilet:', ':shower:', ':bathtub:',

    # Symbols
    ':white_check_mark:', ':heavy_check_mark:', ':ballot_box_with_check:',
    ':x:', ':negative_squared_cross_mark:', ':bangbang:', ':question:',
    ':grey_question:', ':exclamation:', ':grey_exclamation:',
    ':warning:', ':no_entry:', ':stop_sign:', ':no_entry_sign:',
    ':sos:', ':information_source:', ':ok:', ':cool:', ':new:', ':free:',
    ':up:', ':ng:', ':vs:', ':top:', ':end:', ':on:', ':soon:', ':back:',

    # Slack-specific
    ':slack:', ':troll:', ':partyparrot:', ':shipit:', ':octocat:',
    ':github:', ':jira:', ':jenkins:', ':kubernetes:', ':docker:',
}


class SlackEmoteProvider(BaseEmoteProvider):
    """
    Emote provider for Slack platform.

    Uses regex to detect Slack emoji patterns in message text.
    Maintains a list of common emoji for validation.
    """

    def __init__(self):
        """Initialize Slack emote provider."""
        super().__init__("slack")
        self._known_emoji = COMMON_SLACK_EMOJI.copy()

    async def fetch_emotes(
        self,
        channel_id: Optional[str] = None,
        sources: Optional[List[str]] = None
    ) -> List[Emote]:
        """
        Return known Slack emoji as Emote objects.

        Slack custom workspace emoji would require API access.
        This returns the common standard emoji list.

        Args:
            channel_id: Not used (would need Slack API for workspace emotes)
            sources: Not used

        Returns:
            List of common Slack emoji as Emote objects
        """
        emotes = []
        for emoji in self._known_emoji:
            emotes.append(Emote(
                code=emoji,
                source='native',
                platform='slack',
            ))

        logger.debug(f"Returning {len(emotes)} known Slack emoji")
        return emotes

    def detect_emotes_in_text(self, text: str) -> List[Emote]:
        """
        Detect Slack emoji patterns in message text.

        Args:
            text: Message text to scan

        Returns:
            List of detected Emote objects
        """
        emotes = []

        for match in SLACK_EMOTE_PATTERN.finditer(text):
            emoji_code = match.group(0)
            emotes.append(Emote(
                code=emoji_code,
                source='native',
                platform='slack',
            ))

        logger.debug(f"Detected {len(emotes)} Slack emoji in text")
        return emotes

    def is_known_emoji(self, code: str) -> bool:
        """
        Check if code is a known Slack emoji.

        Args:
            code: Emoji code to check (with colons, e.g., ':smile:')

        Returns:
            True if known emoji
        """
        return code in self._known_emoji

    def is_slack_emoji_format(self, text: str) -> bool:
        """
        Check if text matches Slack emoji format.

        Args:
            text: Text to check

        Returns:
            True if matches :emoji: pattern
        """
        return bool(SLACK_EMOTE_PATTERN.fullmatch(text))

    def add_custom_emoji(self, emoji_codes: List[str]) -> None:
        """
        Add custom workspace emoji to known list.

        Args:
            emoji_codes: List of emoji codes to add
        """
        for code in emoji_codes:
            # Ensure proper format
            if not code.startswith(':'):
                code = f':{code}'
            if not code.endswith(':'):
                code = f'{code}:'
            self._known_emoji.add(code)

        logger.debug(f"Added {len(emoji_codes)} custom Slack emoji")

    async def health_check(self) -> bool:
        """Slack provider is always healthy (no external API)."""
        return True
