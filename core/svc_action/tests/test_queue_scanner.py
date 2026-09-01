"""services/queue_scanner.py -- SCAN-based active-queue-key discovery via fakeredis."""

from __future__ import annotations

import fakeredis.aioredis

from services.queue_scanner import scan_action_keys


async def test_finds_all_matching_keys() -> None:
    redis_client = fakeredis.aioredis.FakeRedis()
    await redis_client.lpush("waddles:t:1:c:42:app:waddles.bot.shoutout.default:action", "x")
    await redis_client.lpush("waddles:t:1:c:_tenant:app:waddles.bot.raffle.default:action", "y")
    # non-matching key -- :cfg, not :action -- must not appear in the result
    await redis_client.lpush("waddles:t:1:c:42:app:waddles.bot.shoutout.default:cfg", "z")

    keys = await scan_action_keys(redis_client, pattern="waddles:t:*:c:*:app:*:action")

    assert set(keys) == {
        "waddles:t:1:c:42:app:waddles.bot.shoutout.default:action",
        "waddles:t:1:c:_tenant:app:waddles.bot.raffle.default:action",
    }
    await redis_client.aclose()


async def test_no_matching_keys_returns_empty_list() -> None:
    redis_client = fakeredis.aioredis.FakeRedis()
    keys = await scan_action_keys(redis_client, pattern="waddles:t:*:c:*:app:*:action")
    assert keys == []
    await redis_client.aclose()


async def test_returns_str_keys_not_bytes() -> None:
    redis_client = fakeredis.aioredis.FakeRedis()
    await redis_client.lpush("waddles:t:1:c:42:app:waddles.bot.shoutout.default:action", "x")
    keys = await scan_action_keys(redis_client, pattern="waddles:t:*:c:*:app:*:action")
    assert all(isinstance(k, str) for k in keys)
    await redis_client.aclose()
