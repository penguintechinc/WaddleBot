/**
 * Personal-data export sources for GDPR Art. 15 (access) and Art. 20 (portability).
 *
 * Deliberately free of database imports. `src/config/database.js` creates a
 * pg.Pool at module load, which keeps the event loop alive and makes anything
 * importing it untestable without a live database — so the part with a
 * compliance consequence lives here, and the controller supplies the query
 * function.
 */
/**
 * Every table holding personal data for a user, with the columns the subject is
 * entitled to see.
 *
 * Columns are listed explicitly and never selected with `*`. An access request
 * must disclose personal data, but a response containing `password_hash`,
 * `session_token`, a passkey `public_key` or a verification token would hand
 * the requester credential material — including an attacker who reached an
 * authenticated session. Credentials are deliberately absent; their *existence*
 * is disclosed through metadata such as `device_name` and `created_at`.
 */
const EXPORT_SOURCES = [
  {
    key: 'account',
    sql: `SELECT id, display_name, username, email, avatar_url, is_super_admin,
                 is_vendor, email_verified, last_login, created_at, updated_at, is_active
            FROM hub_users WHERE id = $1`,
  },
  {
    key: 'profile',
    sql: `SELECT display_name, bio, location, location_city, location_state,
                 location_country, website_url, custom_avatar_url, banner_url,
                 visibility, show_activity, show_communities, updated_at
            FROM hub_user_profiles WHERE hub_user_id = $1`,
  },
  {
    key: 'linked_identities',
    sql: `SELECT platform, platform_user_id, platform_username, avatar_url,
                 is_primary, linked_at, last_used
            FROM hub_user_identities WHERE hub_user_id = $1`,
  },
  {
    key: 'sessions',
    sql: `SELECT platform, platform_username, is_active, expires_at, revoked_at, created_at
            FROM hub_sessions WHERE user_id = $1`,
  },
  {
    key: 'passkeys',
    sql: `SELECT device_name, sign_count, created_at, last_used_at
            FROM user_passkeys WHERE user_id = $1`,
  },
  {
    key: 'message_activity',
    sql: `SELECT community_id, platform, platform_username, channel_id, created_at
            FROM activity_message_events WHERE hub_user_id = $1`,
  },
  {
    key: 'watch_activity',
    sql: `SELECT community_id, platform, platform_username, channel_id,
                 session_start, session_end, duration_seconds, created_at
            FROM activity_watch_sessions WHERE hub_user_id = $1`,
  },
  {
    key: 'chat_messages',
    sql: `SELECT community_id, channel_name, sender_platform, sender_username,
                 message_content, message_type, created_at
            FROM hub_chat_messages WHERE sender_hub_user_id = $1`,
  },
  {
    key: 'cookie_consent',
    sql: `SELECT consent_id, preferences, consent_version, consent_method,
                 ip_address, user_agent, consented_at, updated_at, expires_at
            FROM cookie_consent WHERE user_id = $1`,
  },
  {
    key: 'deletion_requests',
    sql: `SELECT requested_at, completed_at, status, deletion_scope
            FROM data_deletion_requests WHERE hub_user_id = $1`,
  },
];

/**
 * Gather a user's personal data across every source.
 *
 * Takes the query function rather than importing it so the set of sources can be
 * tested without a database. A source that fails is reported in `errors` instead
 * of aborting: a partial export the subject can see is more useful than a 500,
 * and silently omitting a table would understate what is held.
 */
export async function collectUserData(queryFn, userId) {
  const data = {};
  const failures = [];

  for (const source of EXPORT_SOURCES) {
    try {
      const result = await queryFn(source.sql, [userId]);
      data[source.key] = result.rows;
    } catch (err) {
      failures.push({ source: source.key, error: err.message });
    }
  }

  return { data, failures };
}

