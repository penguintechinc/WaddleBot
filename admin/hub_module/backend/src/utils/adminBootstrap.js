/**
 * First-run super-admin bootstrap.
 *
 * SECURITY: this module never plants a default/known credential (CWE-798,
 * OWASP A07). The initial super-admin is created ONLY from the
 * INITIAL_ADMIN_EMAIL / INITIAL_ADMIN_PASSWORD environment variables, and
 * ONLY when no super-admin exists yet. If those env vars are unset, no
 * admin account is created -- the boot continues normally (fail closed).
 */
import bcrypt from 'bcrypt';
import { logger } from './logger.js';

const SALT_ROUNDS = 12;

/**
 * Creates the first super-admin account from env-provided credentials.
 * Fail-closed and idempotent -- safe to call on every boot: it skips
 * (with a log message) unless both INITIAL_ADMIN_EMAIL and
 * INITIAL_ADMIN_PASSWORD are set AND no super-admin currently exists.
 *
 * @param {Function} queryFn - parameterized query executor with the same
 *   signature as config/database.js#query: (text, params) => Promise<{rows}>
 * @param {Object} [env] - source of the env vars (overridable for tests)
 * @returns {Promise<{created: boolean, adminId?: number, reason?: string}>}
 */
export async function bootstrapInitialAdmin(queryFn, env = process.env) {
  const adminEmail = env.INITIAL_ADMIN_EMAIL;
  const adminPassword = env.INITIAL_ADMIN_PASSWORD;

  if (!adminEmail || !adminPassword) {
    logger.system(
      'INITIAL_ADMIN_EMAIL/INITIAL_ADMIN_PASSWORD not set - skipping initial admin ' +
        'bootstrap. No default admin account is created. Set both env vars to bootstrap ' +
        'a first super-admin.'
    );
    return { created: false, reason: 'env_not_set' };
  }

  const existing = await queryFn(
    'SELECT id FROM hub_users WHERE is_super_admin = true LIMIT 1'
  );
  if (existing.rows.length > 0) {
    logger.system('A super-admin already exists - skipping initial admin bootstrap');
    return { created: false, reason: 'admin_exists' };
  }

  const passwordHash = await bcrypt.hash(adminPassword, SALT_ROUNDS);
  const result = await queryFn(
    `INSERT INTO hub_users (email, username, password_hash, is_super_admin, is_active, email_verified)
     VALUES ($1, $2, $3, true, true, true)
     ON CONFLICT (email) DO NOTHING
     RETURNING id`,
    [adminEmail, adminEmail, passwordHash]
  );

  if (result.rows.length === 0) {
    // email already belongs to a non-admin account -- never silently
    // escalate an existing identity to super-admin.
    logger.warn('Initial admin bootstrap: INITIAL_ADMIN_EMAIL is already in use by an existing account', {
      email: adminEmail,
    });
    return { created: false, reason: 'email_conflict' };
  }

  const adminId = result.rows[0].id;
  logger.system('Initial super-admin created from INITIAL_ADMIN_EMAIL/INITIAL_ADMIN_PASSWORD', {
    adminId,
  });

  const globalCommunity = await queryFn(
    "SELECT id FROM communities WHERE config->>'is_global' = 'true' LIMIT 1"
  );
  if (globalCommunity.rows.length > 0) {
    await queryFn(
      `INSERT INTO community_members (community_id, user_id, role, is_active, joined_at)
       VALUES ($1, $2, 'member', true, NOW())
       ON CONFLICT (community_id, user_id) DO NOTHING`,
      [globalCommunity.rows[0].id, adminId]
    );
    await queryFn(
      `UPDATE communities SET member_count = (
        SELECT COUNT(*) FROM community_members WHERE community_id = $1 AND is_active = true
      ) WHERE id = $1`,
      [globalCommunity.rows[0].id]
    );
    logger.system('Initial admin added to global community');
  }

  return { created: true, adminId };
}

export default bootstrapInitialAdmin;
