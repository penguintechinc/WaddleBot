"""
Translation Providers Package
=============================

Export all translation provider implementations and the base class.

Available Providers:
- TranslationProvider: Abstract base class
- GoogleTransProvider: Free Google Translate (primary)
- GoogleCloudProvider: Official Google Cloud API (premium, optional)
- WaddleAIProvider: AI-powered fallback via WaddleAI proxy
"""

from .base_provider import TranslationProvider, TranslationResult
from .googletrans_provider import GoogleTransProvider
from .waddleai_provider import WaddleAIProvider

# GoogleCloudProvider is optional - requires google-cloud-translate package
try:
    from .google_cloud_provider import GoogleCloudProvider
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GoogleCloudProvider = None
    GOOGLE_CLOUD_AVAILABLE = False

__all__ = [
    "TranslationProvider",
    "TranslationResult",
    "GoogleTransProvider",
    "GoogleCloudProvider",
    "WaddleAIProvider",
    "GOOGLE_CLOUD_AVAILABLE",
]
