/**
 * GitHub Sync Controller
 * REST handlers for bidirectional GitHub Issues sync with Waddles support tickets.
 */
import {
  createRepoConnection,
  getRepoConnections,
  deleteRepoConnection,
  syncTicketToGithub,
  syncCommentToGithub,
  handleGithubWebhook,
} from '../services/githubSyncService.js';
import { logger } from '../utils/logger.js';

/**
 * GET /admin/:communityId/github-sync/connections
 * List all active GitHub repo connections visible to the authenticated user.
 */
export async function listConnections(req, res) {
  try {
    const userId = req.user.id;
    const connections = await getRepoConnections(userId);
    res.json({ status: 'success', data: connections });
  } catch (err) {
    logger.error({ err }, 'githubSync: listConnections error');
    res.status(err.status || 500).json({ status: 'error', message: err.message });
  }
}

/**
 * POST /admin/:communityId/github-sync/connections
 * Create a new GitHub repo connection.
 * Body: { repo_owner, repo_name, auth_type, token, sync_mode?, default_labels?,
 *         auto_close_on_github_close?, installation_id?, vendor_id?, module_id? }
 */
export async function createConnection(req, res) {
  const { communityId } = req.params;
  const userId = req.user.id;

  const {
    repo_owner,
    repo_name,
    auth_type,
    token,
    sync_mode,
    default_labels,
    auto_close_on_github_close,
    installation_id,
    vendor_id,
    module_id,
  } = req.body;

  if (!repo_owner || !repo_name || !auth_type || !token) {
    return res.status(400).json({
      status: 'error',
      message: 'repo_owner, repo_name, auth_type, and token are required',
    });
  }

  try {
    const connection = await createRepoConnection(userId, {
      community_id: communityId ? parseInt(communityId, 10) : undefined,
      vendor_id,
      module_id,
      repo_owner,
      repo_name,
      sync_mode,
      default_labels,
      auto_close_on_github_close,
      auth_type,
      token,
      installation_id,
    });

    res.status(201).json({ status: 'success', data: connection });
  } catch (err) {
    logger.error({ err }, 'githubSync: createConnection error');
    const status = err.status || 500;
    res.status(status).json({ status: 'error', message: err.message });
  }
}

/**
 * DELETE /admin/:communityId/github-sync/connections/:id
 * Soft-delete a GitHub repo connection.
 */
export async function deleteConnection(req, res) {
  const userId = req.user.id;
  const connectionId = parseInt(req.params.id, 10);

  if (!connectionId || isNaN(connectionId)) {
    return res.status(400).json({ status: 'error', message: 'Invalid connection ID' });
  }

  try {
    await deleteRepoConnection(userId, connectionId);
    res.json({ status: 'success', message: 'Connection deleted' });
  } catch (err) {
    logger.error({ err, connectionId }, 'githubSync: deleteConnection error');
    res.status(err.status || 500).json({ status: 'error', message: err.message });
  }
}

/**
 * POST /github-sync/webhook
 * Receive inbound GitHub webhook events.
 * Authentication is via HMAC-SHA256 signature — NOT session/JWT auth.
 * The raw body must be preserved for signature verification (use express.raw middleware).
 */
export async function receiveWebhook(req, res) {
  const event = req.headers['x-github-event'];
  const signature = req.headers['x-hub-signature-256'];
  const rawBody = req.rawBody || req.body;  // rawBody set by express.raw() middleware

  if (!event) {
    return res.status(400).json({ status: 'error', message: 'Missing X-GitHub-Event header' });
  }
  if (!signature) {
    return res.status(400).json({ status: 'error', message: 'Missing X-Hub-Signature-256 header' });
  }

  let payload;
  try {
    payload = typeof rawBody === 'string' ? JSON.parse(rawBody) : rawBody;
  } catch {
    return res.status(400).json({ status: 'error', message: 'Invalid JSON payload' });
  }

  const repoOwner = payload.repository?.owner?.login;
  const repoName = payload.repository?.name;

  if (!repoOwner || !repoName) {
    return res.status(400).json({ status: 'error', message: 'Missing repository info in payload' });
  }

  try {
    await handleGithubWebhook(repoOwner, repoName, event, payload, rawBody, signature);
    res.json({ status: 'success' });
  } catch (err) {
    logger.error({ err, event, repoOwner, repoName }, 'githubSync: webhook handler error');
    res.status(err.status || 500).json({ status: 'error', message: err.message });
  }
}

/**
 * GET /admin/:communityId/github-sync/ticket/:ticketId/sync-status
 * Return the current sync record(s) for a ticket.
 */
export async function getSyncStatus(req, res) {
  const ticketId = parseInt(req.params.ticketId, 10);

  if (!ticketId || isNaN(ticketId)) {
    return res.status(400).json({ status: 'error', message: 'Invalid ticket ID' });
  }

  try {
    const { db } = await import('../db/index.js');
    const result = await db.query(
      `SELECT tgs.id, tgs.ticket_id, tgs.github_issue_number, tgs.github_issue_node_id,
              tgs.sync_status, tgs.last_synced_at, tgs.last_error, tgs.retry_count,
              tgs.created_at,
              grc.repo_owner, grc.repo_name, grc.sync_mode
       FROM ticket_github_sync tgs
       JOIN github_repo_connections grc ON grc.id = tgs.github_repo_connection_id
       WHERE tgs.ticket_id = $1
       ORDER BY tgs.created_at DESC`,
      [ticketId]
    );

    res.json({ status: 'success', data: result.rows });
  } catch (err) {
    logger.error({ err, ticketId }, 'githubSync: getSyncStatus error');
    res.status(500).json({ status: 'error', message: 'Failed to retrieve sync status' });
  }
}

/**
 * POST /admin/:communityId/github-sync/ticket/:ticketId/sync
 * Manually trigger (or retry) a sync for a ticket to its linked GitHub repo connection.
 * Body: { repo_connection_id }
 */
export async function triggerSync(req, res) {
  const ticketId = parseInt(req.params.ticketId, 10);
  const repoConnectionId = parseInt(req.body?.repo_connection_id, 10);

  if (!ticketId || isNaN(ticketId)) {
    return res.status(400).json({ status: 'error', message: 'Invalid ticket ID' });
  }
  if (!repoConnectionId || isNaN(repoConnectionId)) {
    return res.status(400).json({ status: 'error', message: 'repo_connection_id is required' });
  }

  try {
    const syncRecord = await syncTicketToGithub(ticketId, repoConnectionId);
    res.json({ status: 'success', data: syncRecord });
  } catch (err) {
    logger.error({ err, ticketId, repoConnectionId }, 'githubSync: triggerSync error');
    res.status(err.status || 500).json({ status: 'error', message: err.message });
  }
}
