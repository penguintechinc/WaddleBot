"""Typed exceptions shared by every music provider resolver.

Split into their own module (rather than living in `__init__.py`) because
each provider module (`youtube.py`, `spotify.py`) raises them directly and
`__init__.py` imports those provider modules -- defining them in
`__init__.py` would make that a circular import.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProviderUnavailable(Exception):
    """Raised when a provider's credentials are absent or unusable.

    Not an error condition to crash on -- graceful degradation. Callers
    catch this and disable/hide that provider rather than 500ing.
    """

    provider: str


@dataclass(slots=True)
class TrackNotFound(Exception):
    """Raised when a resolve/search call reaches the provider but finds nothing."""

    query: str
