"""Configuration for welcome_interaction_module."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Runtime configuration for welcome_interaction_module, sourced from env vars."""

    MODULE_NAME = 'welcome_interaction_module'
    MODULE_VERSION = '1.0.0'
    MODULE_PORT = int(os.getenv('MODULE_PORT', '8034'))

    DATABASE_URL: str = os.getenv(
        'DATABASE_URL',
        'postgresql://waddlebot:password@localhost:5432/waddlebot',
    )
    ROUTER_API_URL: str = os.getenv(
        'ROUTER_API_URL',
        'http://router-service:8000/api/v1/router',
    )
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    # social.welcome PostHog flag key -- feature_enabled(flag_key=...) below.
    # OFF by default until validated (general.md Quality Checklist).
    WELCOME_AI_FLAG_KEY: str = os.getenv(
        'WELCOME_AI_FLAG_KEY', 'waddles.social.welcome_ai'
    )

    # Templated welcome used whenever the AI flag is off, or when the AI
    # call fails/times out. {username} is the only substitution variable.
    WELCOME_TEMPLATE: str = os.getenv(
        'WELCOME_TEMPLATE', 'Welcome to the community, {username}! \U0001F44B'
    )

    # ai_interaction_module runs as its own container -- see
    # services/ai_client_service.py for why this is an HTTP adapter rather
    # than a direct Python import.
    AI_INTERACTION_URL: str = os.getenv(
        'AI_INTERACTION_API_URL', 'http://ai-interaction:8005'
    )
    AI_SERVICE_API_KEY: str = os.getenv('AI_SERVICE_API_KEY', '')
    AI_WELCOME_TIMEOUT_SECONDS: float = float(
        os.getenv('AI_WELCOME_TIMEOUT_SECONDS', '5')
    )

    @classmethod
    def validate(cls) -> None:
        """Validate that required configuration values are present.

        Raises:
            EnvironmentError: If any required environment variable is missing
                or obviously invalid.

        """
        errors = []

        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL must be set")

        if not cls.WELCOME_TEMPLATE or '{username}' not in cls.WELCOME_TEMPLATE:
            errors.append("WELCOME_TEMPLATE must contain a {username} placeholder")

        if cls.MODULE_PORT < 1 or cls.MODULE_PORT > 65535:
            errors.append(
                f"MODULE_PORT must be a valid port number (got {cls.MODULE_PORT})"
            )

        if errors:
            msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {e}" for e in errors
            )
            logger.error(msg)
            raise OSError(msg)

        logger.info(
            "Config validated: module=%s version=%s port=%d",
            cls.MODULE_NAME,
            cls.MODULE_VERSION,
            cls.MODULE_PORT,
        )
