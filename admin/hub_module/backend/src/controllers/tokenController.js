/**
 * PAT/CAT Token Controller
 * PAT (Personal Access Token): wdl_u_<random32> — acts as the token owner user
 * CAT (Community Access Token): wdl_c_<random32> — non-human service principal
 */
import crypto from 'crypto';
import { query } from '../config/database.js';
import logger from '../utils/logger.js';

const CAT_QUOTA_STANDARD = 5;
const CAT_QUOTA_PREMIUM = 10;

/**
 * Generate a token string and its SHA-256 hash.
 * Returns { token, hash } — token is returned to the user once, hash is stored.
 */
function generateToken(prefix) {
  const random = crypto.randomBytes(24).toString('hex'); // 48 hex chars
  const token = `${prefix}${random}`;
  const hash = crypto.createHash('sha256').update(token).digest('hex');
  return { token, hash };
}

// ── PAT Endpoints ──────────────────────────────────────────────

/**
 * Get current user's PAT metadata (no hash, no plaintext)
 */
export async function getPAT(req, res, next) {
  try {
    const result = await query(
      `SELECT id, name, scope_ceiling, created_at, last_used_at, expires_at, is_revoked
       FROM user_access_tokens
       WHERE user_id = $1 AND is_revoked = FALSE`,
      [req.user.id]
    );
    res.json({ pat: result.rows[0] || null });
  } catch (err) {
    logger.error('Failed to get PAT', { error: err.message });
    next(err);
  }
}

/**
 * Create a new PAT for the current user (one per user — 409 if exists)
 */
export async function createPAT(req, res, next) {
  try {
    const { name, scope_ceiling, expires_at } = req.body;

    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Token name is required' });
    }

    // Enforce one-per-user
    const existing = await query(
      'SELECT id FROM user_access_tokens WHERE user_id = $1 AND is_revoked = FALSE',
      [req.user.id]
    );
    if (existing.rows.length > 0) {
      return res.status(409).json({
        error: 'You already have an active PAT. Revoke it before creating a new one.'
      });
    }

    const { token, hash } = generateToken('wdl_u_');

    await query(
      `INSERT INTO user_access_tokens (user_id, name, token_hash, scope_ceiling, expires_at)
       VALUES ($1, $2, $3, $4, $5)`,
      [
        req.user.id,
        name.trim(),
        hash,
        scope_ceiling && scope_ceiling.length > 0 ? scope_ceiling : null,
        expires_at || null
      ]
    );

    // Return plaintext token ONCE — never again
    res.status(201).json({
      token,
      message: 'Store this token securely — it will not be shown again.'
    });
  } catch (err) {
    logger.error('Failed to create PAT', { error: err.message });
    next(err);
  }
}

/**
 * Revoke the current user's PAT
 */
export async function revokePAT(req, res, next) {
  try {
    const result = await query(
      `UPDATE user_access_tokens
       SET is_revoked = TRUE
       WHERE user_id = $1 AND is_revoked = FALSE
       RETURNING id`,
      [req.user.id]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'No active PAT found' });
    }
    res.json({ message: 'PAT revoked' });
  } catch (err) {
    logger.error('Failed to revoke PAT', { error: err.message });
    next(err);
  }
}

// ── CAT Endpoints ──────────────────────────────────────────────

/**
 * List community's CATs (metadata only, no hashes)
 */
export async function listCATs(req, res, next) {
  try {
    const { communityId } = req.params;

    const result = await query(
      `SELECT cat.id, cat.name, cat.scopes, cat.created_at, cat.last_used_at,
              cat.expires_at, cat.is_revoked, hu.display_name as created_by_name
       FROM community_access_tokens cat
       LEFT JOIN hub_users hu ON cat.created_by_user_id = hu.id
       WHERE cat.community_id = $1 AND cat.is_revoked = FALSE
       ORDER BY cat.created_at DESC`,
      [communityId]
    );

    const quota = CAT_QUOTA_STANDARD; // TODO: check premium tier for CAT_QUOTA_PREMIUM
    res.json({
      tokens: result.rows,
      quota,
      used: result.rows.length
    });
  } catch (err) {
    logger.error('Failed to list CATs', { error: err.message });
    next(err);
  }
}

/**
 * Create a CAT for a community (scopes required, quota enforced)
 */
export async function createCAT(req, res, next) {
  try {
    const { communityId } = req.params;
    const { name, scopes, expires_at } = req.body;

    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Token name is required' });
    }
    if (!scopes || !Array.isArray(scopes) || scopes.length === 0) {
      return res.status(400).json({ error: 'At least one scope is required for CATs' });
    }

    // Enforce quota
    const countResult = await query(
      'SELECT COUNT(*) FROM community_access_tokens WHERE community_id = $1 AND is_revoked = FALSE',
      [communityId]
    );
    const currentCount = parseInt(countResult.rows[0].count);
    const quota = CAT_QUOTA_STANDARD;
    if (currentCount >= quota) {
      return res.status(409).json({
        error: `CAT quota reached (${quota}). Revoke an existing token before creating a new one.`
      });
    }

    // Validate scopes against catalog
    const validScopes = await query('SELECT scope_key FROM permission_scopes');
    const validKeys = new Set(validScopes.rows.map(r => r.scope_key));
    const invalidScopes = scopes.filter(s => !validKeys.has(s));
    if (invalidScopes.length > 0) {
      return res.status(400).json({
        error: `Invalid scopes: ${invalidScopes.join(', ')}`
      });
    }

    const { token, hash } = generateToken('wdl_c_');

    await query(
      `INSERT INTO community_access_tokens (community_id, created_by_user_id, name, token_hash, scopes, expires_at)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [communityId, req.user.id, name.trim(), hash, scopes, expires_at || null]
    );

    res.status(201).json({
      token,
      message: 'Store this token securely — it will not be shown again.'
    });
  } catch (err) {
    logger.error('Failed to create CAT', { error: err.message });
    next(err);
  }
}

/**
 * Revoke a specific CAT
 */
export async function revokeCAT(req, res, next) {
  try {
    const { communityId, tokenId } = req.params;
    const result = await query(
      `UPDATE community_access_tokens
       SET is_revoked = TRUE
       WHERE id = $1 AND community_id = $2 AND is_revoked = FALSE
       RETURNING id`,
      [tokenId, communityId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Token not found' });
    }
    res.json({ message: 'CAT revoked' });
  } catch (err) {
    logger.error('Failed to revoke CAT', { error: err.message });
    next(err);
  }
}

/**
 * Return permission scopes catalog
 */
export async function listScopes(req, res, next) {
  try {
    const result = await query(
      'SELECT scope_key, display_name, description, category FROM permission_scopes ORDER BY category, display_name'
    );
    res.json({ scopes: result.rows });
  } catch (err) {
    logger.error('Failed to list scopes', { error: err.message });
    next(err);
  }
}
