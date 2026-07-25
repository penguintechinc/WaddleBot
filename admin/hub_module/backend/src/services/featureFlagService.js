/**
 * Feature Flag Service - shared helpers for the feature-flag admin surface.
 *
 * Covers three concerns shared by the community-scoped controller
 * (featureFlagController.js) and the superadmin global controller
 * (featureFlagAdminController.js):
 *   1. Input validation constants (flag key format, platform allowlist).
 *   2. Append-only audit-trail inserts (feature_flag_audit).
 *   3. Cache-invalidation publish to the "feature_flags:reload" Redis channel.
 */
import { logger } from '../utils/logger.js';
import { publish } from '../config/redis.js';

/**
 * Allowed platform values for a flag scope. `null` (all platforms) is handled
 * separately by the callers and is always valid.
 * Mirrors the bot's supported platform set.
 */
export const PLATFORM_ALLOWLIST = [
  'twitch',
  'discord',
  'slack',
  'youtube',
  'kick',
  'teams',
  'mattermost',
  'googlechat',
];

/** flag_key format per the schema contract: lowercase, digits, dot, dash, underscore. */
export const FLAG_KEY_REGEX = /^[a-z0-9_.-]+$/;

/**
 * Normalize/validate a platform value coming from a request body.
 * Returns { platform: string|null } on success or { error: string } on failure.
 */
export function normalizePlatform(value) {
  if (value === undefined || value === null || value === '' || value === 'all') {
    return { platform: null };
  }
  if (typeof value !== 'string' || !PLATFORM_ALLOWLIST.includes(value)) {
    return { error: `platform must be null/all or one of: ${PLATFORM_ALLOWLIST.join(', ')}` };
  }
  return { platform: value };
}

/**
 * Validate a rollout percentage. Returns { rolloutPct: number } or { error }.
 * Accepts undefined → defaults to 100.
 */
export function normalizeRolloutPct(value) {
  if (value === undefined || value === null || value === '') {
    return { rolloutPct: 100 };
  }
  const n = Number(value);
  if (!Number.isInteger(n) || n < 0 || n > 100) {
    return { error: 'rollout_pct must be an integer between 0 and 100' };
  }
  return { rolloutPct: n };
}

/** Validate a flag_key. Returns { flagKey } or { error }. */
export function normalizeFlagKey(value) {
  if (typeof value !== 'string' || value.length === 0 || value.length > 100) {
    return { error: 'flag_key is required and must be at most 100 characters' };
  }
  if (!FLAG_KEY_REGEX.test(value)) {
    return { error: 'flag_key may only contain lowercase letters, digits, dot, dash and underscore' };
  }
  return { flagKey: value };
}

/**
 * Build the "actor" string stored in updated_by / changed_by (VARCHAR 255).
 */
export function actorFromRequest(req) {
  return req.user?.email || req.user?.username || (req.user?.id ? String(req.user.id) : 'unknown');
}

/**
 * Pick the highest-specificity feature_flags row for a
 * (community_id, platform) lookup.
 *
 * EXACT port of the router's resolution
 * (libs/flask_core/flask_core/feature_flags.py, _pick_most_specific):
 * community specificity dominates platform specificity, so a community-scoped
 * row always beats a global row even when the global row is platform-specific.
 * Ranking (first match wins):
 *   1. (community_id, platform)   score 22
 *   2. (community_id, NULL)       score 21
 *   3. (NULL, platform)           score 12
 *   4. (NULL, NULL)               score 11
 *
 * @param {Array<Object>} rows - feature_flags rows (community_id/platform may be null)
 * @param {number|null} communityId - lookup community scope
 * @param {string|null} platform - lookup platform scope
 * @returns {Object|null} the winning row, or null when nothing matches
 */
export function pickMostSpecific(rows, communityId, platform) {
  let best = null;
  let bestScore = -1;
  for (const row of rows) {
    const commSpecific = row.community_id !== null && row.community_id === communityId;
    const commGlobal = row.community_id === null;
    if (!commSpecific && !commGlobal) continue;

    const platSpecific = row.platform !== null && platform !== null && row.platform === platform;
    const platGlobal = row.platform === null;
    if (!platSpecific && !platGlobal) continue;

    // Community rank weighted above platform rank so it always dominates.
    const score = (commSpecific ? 2 : 1) * 10 + (platSpecific ? 2 : 1);
    if (score > bestScore) {
      bestScore = score;
      best = row;
    }
  }
  return best;
}

/** Scope label for a winning row, e.g. 'community-all' or 'global-platform'. */
function scopeOf(row) {
  if (!row) return null;
  const comm = row.community_id !== null ? 'community' : 'global';
  const plat = row.platform !== null ? 'platform' : 'all';
  return `${comm}-${plat}`;
}

function toIso(value) {
  return value?.toISOString?.() || value || null;
}

/**
 * Build the community admin's merged flag view.
 *
 * For each displayed (flag_key, platform) combination present in either the
 * global rows or this community's overrides, the effective state is resolved
 * with the router's exact specificity ranking (pickMostSpecific above):
 * community override at that platform → community override at platform NULL
 * → global at that platform → global at platform NULL. Both effective_enabled
 * and effective_rollout_pct come from the single winning row, so the admin
 * page always mirrors actual bot behavior (e.g. a community all-platform
 * override beats a platform-specific global row).
 *
 * Pure function — no DB access — so it is directly unit-testable.
 *
 * @param {Array<Object>} globalRows - feature_flags rows with community_id NULL
 * @param {Array<Object>} overrideRows - feature_flags rows for this community
 * @param {number} communityId
 * @returns {Array<Object>} display rows
 */
export function resolveEffectiveFlags(globalRows, overrideRows, communityId) {
  const byKey = new Map();
  for (const row of [...globalRows, ...overrideRows]) {
    if (!byKey.has(row.flag_key)) byKey.set(row.flag_key, []);
    byKey.get(row.flag_key).push(row);
  }

  const flags = [];
  const sortedKeys = [...byKey.keys()].sort();
  for (const flagKey of sortedKeys) {
    const rows = byKey.get(flagKey);

    // Display one row per distinct platform scope (null = all platforms first).
    const platformSet = new Map();
    for (const row of rows) platformSet.set(row.platform ?? '*', row.platform ?? null);
    const platforms = [...platformSet.values()].sort((a, b) => {
      if (a === null) return -1;
      if (b === null) return 1;
      return a < b ? -1 : a > b ? 1 : 0;
    });

    for (const platform of platforms) {
      // Winner across ALL candidate rows — mirrors the router's runtime lookup.
      const winner = pickMostSpecific(rows, communityId, platform);
      // What the router would resolve if this community had no overrides.
      const globalWinner = pickMostSpecific(
        rows.filter((r) => r.community_id === null),
        null,
        platform
      );
      // Exact-key rows (used for edit/revert actions and metadata).
      const exactOverride = rows.find(
        (r) => r.community_id === communityId && (r.platform ?? null) === platform
      ) || null;
      const exactGlobal = rows.find(
        (r) => r.community_id === null && (r.platform ?? null) === platform
      ) || null;

      const winnerIsOverride = Boolean(winner && winner.community_id !== null);
      const meta = exactOverride || exactGlobal || winner || {};

      flags.push({
        flag_key: flagKey,
        platform,
        description: exactGlobal?.description ?? winner?.description ?? null,
        // Which row actually won (matches bot behavior) — drives the badge.
        is_override: winnerIsOverride,
        winning_scope: scopeOf(winner),
        winning_override_id: winnerIsOverride ? winner.id : null,
        // Exact override at this (flag_key, platform), if any — the target for
        // edit/revert actions (may differ from the winning row).
        override_id: exactOverride ? exactOverride.id : null,
        effective_enabled: winner ? winner.is_enabled : null,
        effective_rollout_pct: winner ? winner.rollout_pct : null,
        global_enabled: globalWinner ? globalWinner.is_enabled : null,
        global_rollout_pct: globalWinner ? globalWinner.rollout_pct : null,
        updated_by: meta.updated_by ?? null,
        updated_at: toIso(meta.updated_at),
      });
    }
  }
  return flags;
}

/**
 * Insert an append-only audit row. MUST be called inside the same transaction
 * as the mutation it records (pass the transaction client).
 *
 * @param {import('pg').PoolClient} client - transaction client
 * @param {Object} entry
 * @param {string} entry.flagKey
 * @param {number|null} entry.communityId
 * @param {string|null} entry.platform
 * @param {'created'|'updated'|'deleted'} entry.action
 * @param {Object|null} entry.oldValue
 * @param {Object|null} entry.newValue
 * @param {string} entry.changedBy
 */
export async function insertFlagAudit(client, { flagKey, communityId, platform, action, oldValue, newValue, changedBy }) {
  await client.query(
    `INSERT INTO feature_flag_audit
       (flag_key, community_id, platform, action, old_value, new_value, changed_by)
     VALUES ($1, $2, $3, $4, $5, $6, $7)`,
    [
      flagKey,
      communityId ?? null,
      platform ?? null,
      action,
      oldValue === undefined || oldValue === null ? null : JSON.stringify(oldValue),
      newValue === undefined || newValue === null ? null : JSON.stringify(newValue),
      changedBy,
    ]
  );
}

/**
 * Publish a cache-invalidation message so the runtime services drop their
 * cached copy of a flag.
 *
 * CACHE-INVALIDATION CONTRACT: publish JSON {"flag_key": "...", "community_id": <int|null>}
 * to the Redis channel "feature_flags:reload". The Python router subscribes to
 * this channel and invalidates its cached flag decisions.
 *
 * Fire-and-forget: this never throws into the request path. If Redis is
 * unavailable the failure is logged at warn level and the mutation still
 * succeeds (runtime caches simply expire on their own TTL).
 */
export const FEATURE_FLAG_RELOAD_CHANNEL = 'feature_flags:reload';

export async function publishReload(flagKey, communityId) {
  const payload = { flag_key: flagKey, community_id: communityId ?? null };
  try {
    const delivered = await publish(FEATURE_FLAG_RELOAD_CHANNEL, JSON.stringify(payload));
    if (delivered) {
      logger.debug('Published feature_flags reload', {
        channel: FEATURE_FLAG_RELOAD_CHANNEL,
        payload,
      });
    } else {
      logger.warn('feature_flags reload not published — Redis unavailable', {
        channel: FEATURE_FLAG_RELOAD_CHANNEL,
        payload,
      });
    }
  } catch (err) {
    logger.warn('feature_flags reload publish failed', {
      channel: FEATURE_FLAG_RELOAD_CHANNEL,
      payload,
      error: err.message,
    });
  }
}

export default {
  PLATFORM_ALLOWLIST,
  FLAG_KEY_REGEX,
  FEATURE_FLAG_RELOAD_CHANNEL,
  normalizePlatform,
  normalizeRolloutPct,
  normalizeFlagKey,
  actorFromRequest,
  pickMostSpecific,
  resolveEffectiveFlags,
  insertFlagAudit,
  publishReload,
};
