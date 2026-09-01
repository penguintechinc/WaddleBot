"""Discover active process->action Valkey queue keys for the BRPOP fan-in loop.

Valkey has no "subscribe to future keys matching a pattern" primitive for
plain lists, so the runner periodically `SCAN`s for keys matching
`waddles:t:*:c:*:app:*:action` (the exact `bundle_stream_key(..., stage=
"action")` shape from libs/flask_core/flask_core/stream_pipeline.py, used
here as a plain Valkey list rather than a Stream) and blocks on the current
snapshot via `BRPOP`. `SCAN` (cursor-based, non-blocking) is used instead
of `KEYS` -- `KEYS` blocks the whole Valkey server for the duration of the
scan on a large keyspace, `SCAN` does not.
"""

from __future__ import annotations

import redis.asyncio as redis


async def scan_action_keys(
    redis_client: redis.Redis, *, pattern: str, count: int = 500
) -> list[str]:
    """Return every currently-existing key matching `pattern` via a full `SCAN` cursor walk.

    Returns `str` keys (decoded) regardless of the client's `decode_responses`
    setting, so callers never have to branch on bytes-vs-str.
    """
    keys: list[str] = []
    cursor = 0
    while True:
        cursor, batch = await redis_client.scan(cursor=cursor, match=pattern, count=count)
        for key in batch:
            keys.append(key.decode("utf-8") if isinstance(key, bytes) else key)
        if cursor == 0:
            break
    return keys
