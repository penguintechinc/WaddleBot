/**
 * Feature Flag Admin Controller - superadmin surface.
 *
 * Superadmins manage GLOBAL flags (community_id NULL) and view the full audit
 * trail. All mutations force community_id NULL, run in a transaction with the
 * append-only feature_flag_audit INSERT, then publish a reload message.
 *
 * Kept in a dedicated controller (mounted from routes/superadmin.js) to match
 * the existing pattern where superadmin.js aggregates several focused
 * controllers (userManagementController, analyticsController, etc.).
 */
import { query, transaction } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import {
  normalizeFlagKey,
  normalizePlatform,
  normalizeRolloutPct,
  actorFromRequest,
  insertFlagAudit,
  publishReload,
} from '../services/featureFlagService.js';

const SCHEMA_ERROR_CODES = ['42P01', '42703', '42883'];
function isSchemaError(err) {
  return SCHEMA_ERROR_CODES.includes(err?.code);
}

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
 * GET /api/v1/superadmin/feature-flags
 * List all GLOBAL flags with a count of community overrides per flag_key.
 */
export async function listGlobalFlags(req, res, next) {
  try {
    const search = req.query.search || '';
    const params = [];
    let where = 'WHERE g.community_id IS NULL';
    if (search) {
      params.push(`%${search}%`);
      where += ` AND (g.flag_key ILIKE $${params.length} OR g.description ILIKE $${params.length})`;
    }

    const result = await query(
      `SELECT g.*,
              (SELECT COUNT(*) FROM feature_flags o
                WHERE o.flag_key = g.flag_key AND o.community_id IS NOT NULL) AS override_count
         FROM feature_flags g
         ${where}
         ORDER BY g.flag_key, g.platform NULLS FIRST`,
      params
    );

    const flags = result.rows.map((row) => ({
      ...serializeFlag(row),
      override_count: parseInt(row.override_count || 0, 10),
    }));

    res.json({ success: true, flags });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, flags: [] });
    }
    next(err);
  }
}

/**
 * POST /api/v1/superadmin/feature-flags
 * Create a GLOBAL flag (community_id NULL).
 */
export async function createGlobalFlag(req, res, next) {
  try {
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

    const existing = await query(
      `SELECT id FROM feature_flags
        WHERE flag_key = $1 AND community_id IS NULL
          AND COALESCE(platform, '*') = COALESCE($2, '*')`,
      [flagKey, platform]
    );
    if (existing.rows.length > 0) {
      return next(errors.conflict('A global flag with this key/platform already exists'));
    }

    const created = await transaction(async (client) => {
      const result = await client.query(
        `INSERT INTO feature_flags
           (flag_key, community_id, platform, is_enabled, rollout_pct, description, updated_by)
         VALUES ($1, NULL, $2, $3, $4, $5, $6)
         RETURNING *`,
        [flagKey, platform, isEnabled, rolloutPct, description, actor]
      );
      const row = result.rows[0];
      await insertFlagAudit(client, {
        flagKey,
        communityId: null,
        platform,
        action: 'created',
        oldValue: null,
        newValue: serializeFlag(row),
        changedBy: actor,
      });
      return row;
    });

    await publishReload(flagKey, null);
    logger.audit('Global feature flag created', { adminId: req.user?.id, flagKey, platform });

    res.status(201).json({ success: true, flag: serializeFlag(created) });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /api/v1/superadmin/feature-flags/:id
 * Update a GLOBAL flag. The target row must be global (community_id NULL).
 */
export async function updateGlobalFlag(req, res, next) {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return next(errors.badRequest('Invalid flag id'));

    const existing = await query('SELECT * FROM feature_flags WHERE id = $1', [id]);
    if (existing.rows.length === 0) {
      return next(errors.notFound('Feature flag not found'));
    }
    const current = existing.rows[0];
    if (current.community_id !== null) {
      return next(errors.badRequest('This endpoint only manages global flags; use the community endpoint for overrides'));
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
        communityId: null,
        platform: row.platform,
        action: 'updated',
        oldValue: serializeFlag(current),
        newValue: serializeFlag(row),
        changedBy: actor,
      });
      return row;
    });

    await publishReload(updated.flag_key, null);
    logger.audit('Global feature flag updated', { adminId: req.user?.id, flagKey: updated.flag_key });

    res.json({ success: true, flag: serializeFlag(updated) });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /api/v1/superadmin/feature-flags/:id
 * Delete a GLOBAL flag. The target row must be global (community_id NULL).
 */
export async function deleteGlobalFlag(req, res, next) {
  try {
    const id = parseInt(req.params.id, 10);
    if (isNaN(id)) return next(errors.badRequest('Invalid flag id'));

    const existing = await query('SELECT * FROM feature_flags WHERE id = $1', [id]);
    if (existing.rows.length === 0) {
      return next(errors.notFound('Feature flag not found'));
    }
    const current = existing.rows[0];
    if (current.community_id !== null) {
      return next(errors.badRequest('This endpoint only manages global flags'));
    }

    const actor = actorFromRequest(req);
    await transaction(async (client) => {
      await client.query('DELETE FROM feature_flags WHERE id = $1', [id]);
      await insertFlagAudit(client, {
        flagKey: current.flag_key,
        communityId: null,
        platform: current.platform,
        action: 'deleted',
        oldValue: serializeFlag(current),
        newValue: null,
        changedBy: actor,
      });
    });

    await publishReload(current.flag_key, null);
    logger.audit('Global feature flag deleted', { adminId: req.user?.id, flagKey: current.flag_key });

    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /api/v1/superadmin/feature-flags/audit
 * Paginated audit trail, optionally filtered by flag_key.
 */
export async function listAudit(req, res, next) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;
    const flagKey = req.query.flag_key || '';

    const params = [];
    let where = 'WHERE 1=1';
    if (flagKey) {
      params.push(flagKey);
      where += ` AND flag_key = $${params.length}`;
    }

    const countResult = await query(`SELECT COUNT(*) AS count FROM feature_flag_audit ${where}`, params);
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    const result = await query(
      `SELECT id, flag_key, community_id, platform, action, old_value, new_value, changed_by, changed_at
         FROM feature_flag_audit
         ${where}
         ORDER BY changed_at DESC, id DESC
         LIMIT $${params.length + 1} OFFSET $${params.length + 2}`,
      [...params, limit, offset]
    );

    const entries = result.rows.map((row) => ({
      id: row.id,
      flag_key: row.flag_key,
      community_id: row.community_id,
      platform: row.platform,
      action: row.action,
      old_value: row.old_value,
      new_value: row.new_value,
      changed_by: row.changed_by,
      changed_at: row.changed_at?.toISOString?.() || row.changed_at,
    }));

    res.json({
      success: true,
      entries,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    if (isSchemaError(err)) {
      return res.json({ success: true, entries: [], pagination: { page: 1, limit: 25, total: 0, totalPages: 0 } });
    }
    next(err);
  }
}

export default {
  listGlobalFlags,
  createGlobalFlag,
  updateGlobalFlag,
  deleteGlobalFlag,
  listAudit,
};
