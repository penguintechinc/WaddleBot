"""Best-effort PII redaction for prompts sent to EXTERNAL BYOK model APIs.

Applied only by `clients.py`'s `OpenAIClient`/`AnthropicClient` -- the two
adapters whose traffic leaves PenguinTech's infrastructure entirely (a
community's own OpenAI/Anthropic account, via BYOK). The free/premium
Ollama tiers stay on a self-hosted endpoint and are intentionally NOT
redacted here -- redaction is an egress-boundary control, not a blanket
content filter.

Pattern-based and best-effort by design (`security.md` PII tokenization is
the real control upstream of this; this is defense in depth for whatever
raw text still reaches the prompt): catches the structurally-obvious
cases -- email addresses and token/secret-shaped strings (API keys,
`Authorization: Bearer ...` headers, JWTs). Never raises; unmatched text
passes through unchanged.
"""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")

# Token/secret-shaped strings worth redacting on sight:
#   - OpenAI/Anthropic-style secret keys ("sk-...")
#   - WaddleAI's own BYOK-adjacent key format ("wa-...")
#   - "Authorization: Bearer <token>" headers pasted into a prompt
#   - JWTs (three base64url segments separated by ".")
_TOKEN_RE = re.compile(
    r"""
    \bsk-[A-Za-z0-9_-]{10,}\b
    | \bwa-[A-Za-z0-9_-]{10,}\b
    | \bBearer\s+[A-Za-z0-9._-]{10,}\b
    | \b[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b
    """,
    re.VERBOSE,
)

_EMAIL_PLACEHOLDER = "[REDACTED_EMAIL]"
_TOKEN_PLACEHOLDER = "[REDACTED_TOKEN]"


def redact_pii(text: str) -> str:
    """Redact obvious email addresses and token/secret-shaped strings from `text`.

    Args:
        text: Raw prompt text about to be sent to an external provider.

    Returns:
        `text` with clear-case PII/secrets replaced by placeholders. Falsy
        input is returned unchanged.
    """
    if not text:
        return text
    redacted = _EMAIL_RE.sub(_EMAIL_PLACEHOLDER, text)
    redacted = _TOKEN_RE.sub(_TOKEN_PLACEHOLDER, redacted)
    return redacted


__all__ = ["redact_pii"]
