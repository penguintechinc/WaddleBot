/**
 * GitHub Sync Service
 * Handles bidirectional sync between Waddles support tickets and GitHub Issues.
 * Uses AES-256-GCM for token encryption at rest.
 * GitHub API calls use Node 18+ built-in fetch — no axios/octokit dependency.
 */
import crypto from 'crypto';
import { db } from '../db/index.js';
import { logger } from '../utils/logger.js';

const ENCRYPTION_KEY_HEX = process.env.GITHUB_SYNC_ENCRYPTION_KEY;
const GITHUB_API_BASE = 'https://api.github.com';
const MAX_RETRY_COUNT = 3;

// ── Encryption helpers ────────────────────────────────────────────────────────

function getEncryptionKey() {
  if (!ENCRYPTION_KEY_HEX) {
    throw new Error('GITHUB_SYNC_ENCRYPTION_KEY environment variable is not set');
  }
  const key = Buffer.from(ENCRYPTION_KEY_HEX, 'hex');
  if (key.length !== 32) {
    throw new Error('GITHUB_SYNC_ENCRYPTION_KEY must be a 64-character hex string (32 bytes)');
  }
  return key;
}

/**
 * Encrypt a plaintext token using AES-256-GCM.
 * Returns a base64 string: iv (12 bytes) + authTag (16 bytes) + ciphertext.
 * @param {string} plaintext
 * @returns {string}
 */
function encryptToken(plaintext) {
  const key = getEncryptionKey();
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', key, iv);
  const encrypted = Buffer.concat([cipher.update(plaintext, 'utf8'), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return Buffer.concat([iv, authTag, encrypted]).toString('base64');
}

/**
 * Decrypt a token encrypted by encryptToken.
 * @param {string} encryptedBase64
 * @returns {string}
 */
function decryptToken(encryptedBase64) {
  const key = getEncryptionKey();
  const buf = Buffer.from(encryptedBase64, 'base64');
  const iv = buf.subarray(0, 12);
  const authTag = buf.subarray(12, 28);
  const ciphertext = buf.subarray(28);
  const decipher = crypto.createDecipheriv('aes-256-gcm', key, iv);
  decipher.setAuthTag(authTag);
  return Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf8');
}

/**
 * Mask a token for safe display: show last 4 chars, mask the rest.
 * @param {string} token
 * @returns {string}
 */
function maskToken(token) {
  if (!token || token.length < 8) return '****';
  return `****${token.slice(-4)}`;
}

/**
 * Generate a cryptographically random webhook secret.
 * @returns {string}
 */
function generateWebhookSecret() {
  return crypto.randomBytes(32).toString('hex');
}

// ── GitHub API helpers ────────────────────────────────────────────────────────

/**
 * Make an authenticated GitHub REST API request.
 * @param {string} method
 * @param {string} path
 * @param {string} token
 * @param {object|null} body
 * @returns {Promise<{ok: boolean, status: number, data: any}>}
 */
async function githubRequest(method, path, token, body = null) {
  const url = `${GITHUB_API_BASE}${path}`;
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'Content-Type': 'application/json',
    'User-Agent': 'WaddleBot-GithubSync/1.0',
  };

  const options = { method, headers };
  if (body !== null) {
    options.body = JSON.stringify(body);
  }

  const res = await fetch(url, options);
  let data = null;
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) {
    data = await res.json();
  }
  return { ok: res.ok, status: res.status, data };
}

/**
 * Verify a GitHub webhook HMAC-SHA256 signature.
 * @param {Buffer|string} rawBody
 * @param {string} signatureHeader  e.g. "sha256=abc123..."
 * @param {string} secret
 * @returns {boolean}
 */
function verifyWebhookSignature(rawBody, signatureHeader, secret) {
  if (!signatureHeader || !signatureHeader.startsWith('sha256=')) return false;
  const expected = `sha256=${crypto
    .createHmac('sha256', secret)
    .update(rawBody)
    .digest('hex')}`;
  try {
    return crypto.timingSafeEqual(
      Buffer.from(expected, 'utf8'),
      Buffer.from(signatureHeader, 'utf8')
    );
  } catch {
    return false;
  }
}

// ── Sync log helper ───────────────────────────────────────────────────────────

async function writeSyncLog(ticketGithubSyncId, direction, eventType, payload, success, errorMessage = null) {
  try {
    await db.query(
      `INSERT INTO github_sync_log
         (ticket_github_sync_id, direction, event_type, payload, success, error_message)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [ticketGithubSyncId, direction, eventType, JSON.stringify(payload), success, errorMessage]
    );
  } catch (logErr) {
    logger.error({ err: logErr }, 'githubSync: failed to write sync log');
  }
}

// ── Public service methods ────────────────────────────────────────────────────

/**
 * Create a new GitHub repo connection for a user.
 * Validates required fields, encrypts the PAT, generates a webhook secret.
 *
 * @param {number} userId
 * @param {object} connectionData
 * @returns {Promise<object>} Created connection row (token masked)
 */
export async function createRepoConnection(userId, connectionData) {
  const {
    community_id,
    vendor_id,
    module_id,
    repo_owner,
    repo_name,
    sync_mode = 'tickets_only',
    default_labels = ['waddles', 'support'],
    auto_close_on_github_close = true,
    auth_type,
    token,
    installation_id,
  } = connectionData;

  if (!repo_owner || !repo_name) {
    throw Object.assign(new Error('repo_owner and repo_name are required'), { status: 400 });
  }
  if (!auth_type || !['github_app', 'pat'].includes(auth_type)) {
    throw Object.assign(new Error("auth_type must be 'github_app' or 'pat'"), { status: 400 });
  }
  if (!token) {
    throw Object.assign(new Error('token is required'), { status: 400 });
  }
  if (!community_id && !vendor_id) {
    throw Object.assign(new Error('Either community_id or vendor_id is required'), { status: 400 });
  }

  const encryptedToken = encryptToken(token);
  const webhookSecret = generateWebhookSecret();

  const result = await db.query(
    `INSERT INTO github_repo_connections
       (community_id, vendor_id, module_id, repo_owner, repo_name,
        sync_mode, default_labels, auto_close_on_github_close,
        auth_type, encrypted_token, webhook_secret, installation_id)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
     RETURNING id, community_id, vendor_id, module_id, repo_owner, repo_name,
               sync_mode, default_labels, auto_close_on_github_close,
               auth_type, webhook_secret, installation_id, is_active,
               created_at, updated_at`,
    [
      community_id ?? null,
      vendor_id ?? null,
      module_id ?? null,
      repo_owner,
      repo_name,
      sync_mode,
      default_labels,
      auto_close_on_github_close,
      auth_type,
      encryptedToken,
      webhookSecret,
      installation_id ?? null,
    ]
  );

  logger.info({ userId, repoOwner: repo_owner, repoName: repo_name }, 'githubSync: repo connection created');
  return result.rows[0];
}

/**
 * List all GitHub repo connections visible to a user.
 * Tokens are returned masked (last 4 chars) — never in plaintext.
 *
 * @param {number} userId
 * @returns {Promise<object[]>}
 */
export async function getRepoConnections(userId) {
  const result = await db.query(
    `SELECT id, community_id, vendor_id, module_id, repo_owner, repo_name,
            sync_mode, default_labels, auto_close_on_github_close,
            auth_type, encrypted_token, webhook_secret, installation_id,
            is_active, created_at, updated_at
     FROM github_repo_connections
     WHERE is_active = true
       AND (vendor_id = $1 OR community_id IN (
         SELECT community_id FROM community_members WHERE user_id = $1 AND role IN ('admin','owner')
       ))
     ORDER BY created_at DESC`,
    [userId]
  );

  return result.rows.map((row) => {
    let maskedToken = '****';
    try {
      const plain = decryptToken(row.encrypted_token);
      maskedToken = maskToken(plain);
    } catch {
      maskedToken = '****';
    }
    return {
      ...row,
      encrypted_token: undefined,
      token_masked: maskedToken,
    };
  });
}

/**
 * Soft-delete a GitHub repo connection.
 * Only the owning vendor or a community admin may delete a connection.
 *
 * @param {number} userId
 * @param {number} connectionId
 * @returns {Promise<void>}
 */
export async function deleteRepoConnection(userId, connectionId) {
  const existing = await db.query(
    `SELECT id, vendor_id, community_id FROM github_repo_connections WHERE id = $1 AND is_active = true`,
    [connectionId]
  );

  if (existing.rows.length === 0) {
    throw Object.assign(new Error('Connection not found'), { status: 404 });
  }

  const conn = existing.rows[0];

  // Verify the caller owns or admins this connection
  const authCheck = await db.query(
    `SELECT 1 FROM (
       SELECT id FROM hub_users WHERE id = $1 AND id = $2
       UNION
       SELECT cm.user_id FROM community_members cm
       WHERE cm.user_id = $1 AND cm.community_id = $3 AND cm.role IN ('admin','owner')
     ) AS auth_check LIMIT 1`,
    [userId, conn.vendor_id, conn.community_id]
  );

  if (authCheck.rows.length === 0) {
    throw Object.assign(new Error('Forbidden'), { status: 403 });
  }

  await db.query(
    `UPDATE github_repo_connections SET is_active = false, updated_at = NOW() WHERE id = $1`,
    [connectionId]
  );

  logger.info({ userId, connectionId }, 'githubSync: repo connection deleted (soft)');
}

/**
 * Push a Waddles support ticket to GitHub as a new issue.
 * Inserts a ticket_github_sync record tracking the link.
 *
 * @param {number} ticketId
 * @param {number} repoConnectionId
 * @returns {Promise<object>} sync record
 */
export async function syncTicketToGithub(ticketId, repoConnectionId) {
  // Load ticket
  const ticketResult = await db.query(
    `SELECT id, subject, description, status, priority, created_at
     FROM support_tickets WHERE id = $1`,
    [ticketId]
  );
  if (ticketResult.rows.length === 0) {
    throw Object.assign(new Error('Ticket not found'), { status: 404 });
  }
  const ticket = ticketResult.rows[0];

  // Load connection
  const connResult = await db.query(
    `SELECT id, repo_owner, repo_name, encrypted_token, default_labels, webhook_secret
     FROM github_repo_connections WHERE id = $1 AND is_active = true`,
    [repoConnectionId]
  );
  if (connResult.rows.length === 0) {
    throw Object.assign(new Error('Repo connection not found or inactive'), { status: 404 });
  }
  const conn = connResult.rows[0];

  let token;
  try {
    token = decryptToken(conn.encrypted_token);
  } catch (err) {
    throw Object.assign(new Error('Failed to decrypt repo connection token'), { status: 500 });
  }

  const issueBody = [
    ticket.description || '',
    '',
    `---`,
    `*Synced from [WaddleBot](https://waddles.app) support ticket #${ticket.id}*`,
    `Priority: ${ticket.priority || 'normal'} | Status: ${ticket.status}`,
  ].join('\n');

  const { ok, status, data } = await githubRequest(
    'POST',
    `/repos/${conn.repo_owner}/${conn.repo_name}/issues`,
    token,
    {
      title: ticket.subject,
      body: issueBody,
      labels: conn.default_labels || ['waddles', 'support'],
    }
  );

  if (!ok) {
    // Record failure
    const syncInsert = await db.query(
      `INSERT INTO ticket_github_sync
         (ticket_id, github_repo_connection_id, github_issue_number, sync_status, last_error)
       VALUES ($1, $2, 0, 'failed', $3)
       RETURNING id`,
      [ticketId, repoConnectionId, `GitHub API ${status}: ${JSON.stringify(data)}`]
    );
    await writeSyncLog(
      syncInsert.rows[0].id, 'outbound', 'issue_created',
      { ticketId, repoConnectionId },
      false,
      `GitHub API ${status}: ${JSON.stringify(data)}`
    );
    throw Object.assign(new Error(`GitHub API error ${status}`), { status: 502, detail: data });
  }

  const syncInsert = await db.query(
    `INSERT INTO ticket_github_sync
       (ticket_id, github_repo_connection_id, github_issue_number, github_issue_node_id, sync_status)
     VALUES ($1, $2, $3, $4, 'synced')
     RETURNING *`,
    [ticketId, repoConnectionId, data.number, data.node_id]
  );

  await writeSyncLog(
    syncInsert.rows[0].id, 'outbound', 'issue_created',
    { ticketId, issueNumber: data.number, issueUrl: data.html_url },
    true
  );

  logger.info(
    { ticketId, issueNumber: data.number, repo: `${conn.repo_owner}/${conn.repo_name}` },
    'githubSync: ticket synced to GitHub'
  );

  return syncInsert.rows[0];
}

/**
 * Add a comment on the GitHub issue linked to a ticket.
 *
 * @param {number} ticketId
 * @param {string} commentText
 * @param {string} authorName
 * @returns {Promise<void>}
 */
export async function syncCommentToGithub(ticketId, commentText, authorName) {
  const syncResult = await db.query(
    `SELECT tgs.id, tgs.github_issue_number, tgs.github_repo_connection_id,
            grc.repo_owner, grc.repo_name, grc.encrypted_token
     FROM ticket_github_sync tgs
     JOIN github_repo_connections grc ON grc.id = tgs.github_repo_connection_id
     WHERE tgs.ticket_id = $1 AND tgs.sync_status != 'failed'
       AND grc.is_active = true
     LIMIT 1`,
    [ticketId]
  );

  if (syncResult.rows.length === 0) {
    logger.warn({ ticketId }, 'githubSync: no active sync record found for comment sync');
    return;
  }

  const sync = syncResult.rows[0];
  let token;
  try {
    token = decryptToken(sync.encrypted_token);
  } catch {
    logger.error({ ticketId }, 'githubSync: failed to decrypt token for comment sync');
    return;
  }

  const body = `**${authorName}** (via WaddleBot):\n\n${commentText}`;

  const { ok, status, data } = await githubRequest(
    'POST',
    `/repos/${sync.repo_owner}/${sync.repo_name}/issues/${sync.github_issue_number}/comments`,
    token,
    { body }
  );

  await writeSyncLog(
    sync.id, 'outbound', 'comment_added',
    { ticketId, issueNumber: sync.github_issue_number },
    ok,
    ok ? null : `GitHub API ${status}: ${JSON.stringify(data)}`
  );

  if (!ok) {
    logger.error({ ticketId, status }, 'githubSync: failed to post comment to GitHub');
  }
}

/**
 * Handle an inbound GitHub webhook event.
 * Verifies the HMAC-SHA256 signature, dispatches to the appropriate handler.
 *
 * @param {string} repoOwner
 * @param {string} repoName
 * @param {string} event  - X-GitHub-Event header value
 * @param {object} payload
 * @param {Buffer} rawBody  - raw request body (for signature verification)
 * @param {string} signature  - X-Hub-Signature-256 header value
 * @returns {Promise<void>}
 */
export async function handleGithubWebhook(repoOwner, repoName, event, payload, rawBody, signature) {
  // Load connection to get webhook secret
  const connResult = await db.query(
    `SELECT id, webhook_secret FROM github_repo_connections
     WHERE repo_owner = $1 AND repo_name = $2 AND is_active = true
     LIMIT 1`,
    [repoOwner, repoName]
  );

  if (connResult.rows.length === 0) {
    logger.warn({ repoOwner, repoName }, 'githubSync: webhook received for unknown repo connection');
    return;
  }

  const conn = connResult.rows[0];

  if (!verifyWebhookSignature(rawBody, signature, conn.webhook_secret)) {
    logger.warn({ repoOwner, repoName }, 'githubSync: invalid webhook signature');
    throw Object.assign(new Error('Invalid webhook signature'), { status: 401 });
  }

  const issueNumber = payload.issue?.number;
  if (!issueNumber) return;  // not an issue event we care about

  // Find the sync record for this issue
  const syncResult = await db.query(
    `SELECT id, ticket_id FROM ticket_github_sync
     WHERE github_repo_connection_id = $1 AND github_issue_number = $2
     LIMIT 1`,
    [conn.id, issueNumber]
  );

  if (syncResult.rows.length === 0) {
    logger.debug({ repoOwner, repoName, issueNumber }, 'githubSync: webhook for untracked issue — ignoring');
    return;
  }

  const syncRecord = syncResult.rows[0];

  if (event === 'issue_comment' && payload.action === 'created') {
    const commentBody = payload.comment?.body || '';
    const author = payload.comment?.user?.login || 'GitHub User';
    // Avoid echo-looping our own outbound comments
    if (!commentBody.includes('(via WaddleBot)')) {
      await processInboundIssueComment(syncRecord, commentBody, author);
    }
    return;
  }

  if (event === 'issues' && payload.action === 'closed') {
    await processInboundIssueClose(syncRecord);
    return;
  }

  logger.debug({ event, action: payload.action }, 'githubSync: unhandled webhook event');
}

/**
 * Add an inbound GitHub comment as a reply on the Waddles ticket.
 *
 * @param {{id: number, ticket_id: number}} syncRecord
 * @param {string} commentBody
 * @param {string} author
 * @returns {Promise<void>}
 */
export async function processInboundIssueComment(syncRecord, commentBody, author) {
  try {
    await db.query(
      `INSERT INTO support_ticket_comments
         (ticket_id, content, author_name, is_internal, source)
       VALUES ($1, $2, $3, false, 'github')`,
      [syncRecord.ticket_id, commentBody, author]
    );

    await writeSyncLog(syncRecord.id, 'inbound', 'comment_received', { author }, true);

    logger.info({ ticketId: syncRecord.ticket_id, author }, 'githubSync: inbound comment added to ticket');
  } catch (err) {
    await writeSyncLog(syncRecord.id, 'inbound', 'comment_received', { author }, false, err.message);
    logger.error({ err, ticketId: syncRecord.ticket_id }, 'githubSync: failed to add inbound comment');
  }
}

/**
 * Close a Waddles ticket when its linked GitHub issue is closed.
 *
 * @param {{id: number, ticket_id: number}} syncRecord
 * @returns {Promise<void>}
 */
export async function processInboundIssueClose(syncRecord) {
  try {
    // Check auto_close setting for this connection
    const connResult = await db.query(
      `SELECT grc.auto_close_on_github_close
       FROM ticket_github_sync tgs
       JOIN github_repo_connections grc ON grc.id = tgs.github_repo_connection_id
       WHERE tgs.id = $1`,
      [syncRecord.id]
    );

    if (connResult.rows.length === 0 || !connResult.rows[0].auto_close_on_github_close) {
      logger.debug({ syncId: syncRecord.id }, 'githubSync: auto_close disabled, skipping close');
      return;
    }

    await db.query(
      `UPDATE support_tickets SET status = 'closed', updated_at = NOW()
       WHERE id = $1 AND status NOT IN ('closed', 'resolved')`,
      [syncRecord.ticket_id]
    );

    await writeSyncLog(syncRecord.id, 'inbound', 'issue_closed', {}, true);

    logger.info({ ticketId: syncRecord.ticket_id }, 'githubSync: ticket closed from GitHub issue close');
  } catch (err) {
    await writeSyncLog(syncRecord.id, 'inbound', 'issue_closed', {}, false, err.message);
    logger.error({ err, ticketId: syncRecord.ticket_id }, 'githubSync: failed to close ticket from GitHub event');
  }
}

/**
 * Retry failed sync records (retry_count < MAX_RETRY_COUNT) with exponential backoff.
 * Intended to be called by a periodic job (e.g. cron every 5 minutes).
 *
 * @returns {Promise<{retried: number, succeeded: number, failed: number}>}
 */
export async function retryFailedSyncs() {
  const pending = await db.query(
    `SELECT tgs.id AS sync_id, tgs.ticket_id, tgs.github_repo_connection_id,
            tgs.retry_count, tgs.created_at
     FROM ticket_github_sync tgs
     JOIN github_repo_connections grc ON grc.id = tgs.github_repo_connection_id
     WHERE tgs.sync_status = 'failed'
       AND tgs.retry_count < $1
       AND grc.is_active = true
     ORDER BY tgs.created_at ASC
     LIMIT 50`,
    [MAX_RETRY_COUNT]
  );

  const records = pending.rows;
  let succeeded = 0;
  let failed = 0;

  for (const record of records) {
    // Exponential backoff: wait 2^retryCount minutes before retrying
    const backoffMinutes = Math.pow(2, record.retry_count);
    const backoffMs = backoffMinutes * 60 * 1000;
    const msSinceCreated = Date.now() - new Date(record.created_at).getTime();
    if (msSinceCreated < backoffMs) continue;

    try {
      await syncTicketToGithub(record.ticket_id, record.github_repo_connection_id);
      succeeded++;
    } catch (err) {
      failed++;
      await db.query(
        `UPDATE ticket_github_sync
         SET retry_count = retry_count + 1,
             last_error = $1,
             sync_status = CASE WHEN retry_count + 1 >= $2 THEN 'failed' ELSE 'pending' END
         WHERE id = $3`,
        [err.message, MAX_RETRY_COUNT, record.sync_id]
      );
      logger.warn({ syncId: record.sync_id, err: err.message }, 'githubSync: retry failed');
    }
  }

  logger.info({ total: records.length, succeeded, failed }, 'githubSync: retry job completed');
  return { retried: records.length, succeeded, failed };
}
