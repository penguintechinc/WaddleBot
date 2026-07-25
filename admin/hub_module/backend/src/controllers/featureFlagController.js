/**
 * Feature Flag Controller - community admin surface.
 *
 * Community admins manage feature-flag OVERRIDES for their OWN community only.
 * A community admin must NEVER be able to create/update/delete a global row
 * (community_id NULL) or another community's row: community_id is always forced
 * from the :communityId URL param and every mutation re-checks ownership.
 *
 * Every mutation is wrapped in a transaction together with the append-only
 * feature_flag_audit INSERT, then publishes a cache-invalidation message.
 */
import { query, transaction } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import {
  normalizeFlagKey,
  normalizePlatform,
  normalizeRolloutPct,
  actorFromRequest,
  resolveEffectiveFlags,
  insertFlagAudit,
  publishReload,
} from '../services/featureFlagService.js';

/**
 * PostgreSQL error codes for missing schema objects. If migration 068 has not
 * been applied yet, list endpoints degrade to empty data instead of a 500.
 */
const SCHEMA_ERROR_CODES = ['42P01', '42703', '42883'];
function isSchemaError(err) {
  return SCHEMA_ERROR_CODES.includes(err?.code);
}

/** Serialize a feature_flags row for API responses. */
function serializeFlag(row) {
  return {
    id: row.id,
    flag_key: row.flag_key,
    community_id: row.community_id,
    platform: row.platform,
    is_enabled: row.is_enabled,
    rollout_pct: row.rollout_pct,
    description: row.description,
    updated_by: row.updated_by,
    created_at: row.created_at?.toISOString?.() || row.created_at,
    updated_at: row.updated_at?.toISOString?.() || row.updated_at,
  };
}

/**
 * GET /api/v1/admin/:communityId/feature-flags
 * Merged view: every global flag (community_id NULL) plus this community's
 * overrides. Effective state per (flag_key, platform) row is resolved with the
 * router's exact specificity ranking (see resolveEffectiveFlags /
 * libs/flask_core/flask_core/feature_flags.py _pick_most_specific):
 * (community, platform) > (community, NULL) > (NULL, platform) > (NULL, NULL) —
 * so the page always shows what the bot actually does, e.g. a community
 * all-platform override wins over a platform-specific global row.
 */
export async function listCommunityFlags(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const globalsResult = await query(
      `SELECT * FROM feature_flags
        WHERE community_id IS NULL
        ORDER BY flag_key, platform NULLS FIRST`,
      []
    );
    const overridesResult = await query(
      `SELECT * FROM feature_flags
        WHERE community_id = $1
        ORDER BY flag_key, platform NULLS FIRST`,
      [communityId]
    );

    const flags = resolveEffectiveFlags(globalsResult.rows, overridesResult.rows, communityId);

    res.json({ success: true, flags });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, flags: [] });
    }
    next(err);
  }
}

/**
 * POST /api/v1/admin/:communityId/feature-flags
 * Create a community-scoped override. community_id is forced from the URL.
 */
export async function createCommunityOverride(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const keyCheck = normalizeFlagKey(req.body.flag_key);
    if (keyCheck.error) return next(errors.badRequest(keyCheck.error));
    const platCheck = normalizePlatform(req.body.platform);
    if (platCheck.error) return next(errors.badRequest(platCheck.error));
    const pctCheck = normalizeRolloutPct(req.body.rollout_pct);
    if (pctCheck.error) return next(errors.badRequest(pctCheck.error));

    const { flagKey } = keyCheck;
    const { platform } = platCheck;
    const { rolloutPct } = pctCheck;
    const isEnabled = req.body.is_enabled === undefined ? false : Boolean(req.body.is_enabled);
    const description = typeof req.body.description === 'string' ? req.body.description : null;
    const actor = actorFromRequest(req);

    // Reject duplicates for this community + platform (unique per
    // flag_key, COALESCE(community_id,-1), COALESCE(platform,'*')).
    const existing = await query(
      `SELECT id FROM feature_flags
        WHERE flag_key = $1 AND community_id = $2
          AND COALESCE(platform, '*') = COALESCE($3, '*')`,
      [flagKey, communityId, platform]
    );
    if (existing.rows.length > 0) {
      return next(errors.conflict('An override for this flag/platform already exists for this community'));
    }

    const created = await transaction(async (client) => {
      const result = await client.query(
        `INSERT INTO feature_flags
           (flag_key, community_id, platform, is_enabled, rollout_pct, description, updated_by)
         VALUES ($1, $2, $3, $4, $5, $6, $7)
         RETURNING *`,
        [flagKey, communityId, platform, isEnabled, rolloutPct, description, actor]
      );
      const row = result.rows[0];
      await insertFlagAudit(client, {
        flagKey,
        communityId,
        platform,
        action: 'created',
        oldValue: null,
        newValue: serializeFlag(row),
        changedBy: actor,
      });
      return row;
    });

    await publishReload(flagKey, communityId);
    logger.audit('Feature flag override created', { adminId: req.user?.id, communityId, flagKey, platform });

    res.status(201).json({ success: true, flag: serializeFlag(created) });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /api/v1/admin/:communityId/feature-flags/:id
 * Update a community-scoped override. Ownership is re-checked: the row must
 * belong to THIS community (never a global row, never another community).
 */
export async function updateCommunityOverride(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return next(errors.badRequest('Invalid flag id'));

    const existing = await query('SELECT * FROM feature_flags WHERE id = $1', [id]);
    if (existing.rows.length === 0) {
      return next(errors.notFound('Feature flag override not found'));
    }
    const current = existing.rows[0];
    // Guard: a community admin may only touch their own community's overrides.
    if (current.community_id !== communityId) {
      return next(errors.forbidden('Cannot modify a flag outside this community'));
    }

    const updates = [];
    const params = [];
    let idx = 1;

    if (req.body.is_enabled !== undefined) {
      updates.push(`is_enabled = $${idx++}`);
      params.push(Boolean(req.body.is_enabled));
    }
    if (req.body.rollout_pct !== undefined) {
      const pctCheck = normalizeRolloutPct(req.body.rollout_pct);
      if (pctCheck.error) return next(errors.badRequest(pctCheck.error));
      updates.push(`rollout_pct = $${idx++}`);
      params.push(pctCheck.rolloutPct);
    }
    if (req.body.description !== undefined) {
      updates.push(`description = $${idx++}`);
      params.push(typeof req.body.description === 'string' ? req.body.description : null);
    }
    if (updates.length === 0) {
      return next(errors.badRequest('No updates provided'));
    }

    const actor = actorFromRequest(req);
    updates.push(`updated_by = $${idx++}`);
    params.push(actor);
    updates.push('updated_at = NOW()');
    params.push(id);

    const updated = await transaction(async (client) => {
      const result = await client.query(
        `UPDATE feature_flags SET ${updates.join(', ')} WHERE id = $${idx} RETURNING *`,
        params
      );
      const row = result.rows[0];
      await insertFlagAudit(client, {
        flagKey: row.flag_key,
        communityId,
        platform: row.platform,
        action: 'updated',
        oldValue: serializeFlag(current),
        newValue: serializeFlag(row),
        changedBy: actor,
      });
      return row;
    });

    await publishReload(updated.flag_key, communityId);
    logger.audit('Feature flag override updated', { adminId: req.user?.id, communityId, flagKey: updated.flag_key });

    res.json({ success: true, flag: serializeFlag(updated) });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/v1/admin/:communityId/feature-flags/:id
 * Remove a community-scoped override (reverts to the global default).
 */
export async function deleteCommunityOverride(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return next(errors.badRequest('Invalid flag id'));

    const existing = await query('SELECT * FROM feature_flags WHERE id = $1', [id]);
    if (existing.rows.length === 0) {
      return next(errors.notFound('Feature flag override not found'));
    }
    const current = existing.rows[0];
    if (current.community_id !== communityId) {
      return next(errors.forbidden('Cannot delete a flag outside this community'));
    }

    const actor = actorFromRequest(req);
    await transaction(async (client) => {
      await client.query('DELETE FROM feature_flags WHERE id = $1', [id]);
      await insertFlagAudit(client, {
        flagKey: current.flag_key,
        communityId,
        platform: current.platform,
        action: 'deleted',
        oldValue: serializeFlag(current),
        newValue: null,
        changedBy: actor,
      });
    });

    await publishReload(current.flag_key, communityId);
    logger.audit('Feature flag override deleted', { adminId: req.user?.id, communityId, flagKey: current.flag_key });

    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

export default {
  listCommunityFlags,
  createCommunityOverride,
  updateCommunityOverride,
  deleteCommunityOverride,
};
