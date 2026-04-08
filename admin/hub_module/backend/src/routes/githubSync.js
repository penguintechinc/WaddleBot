/**
 * GitHub Sync Routes
 * Bidirectional sync between Waddles support tickets and GitHub Issues.
 *
 * Connection management routes require JWT auth (requireAuth + requireCommunityAdmin).
 * Webhook receiver is public — authentication is via HMAC-SHA256 payload signature.
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import {
  listConnections,
  createConnection,
  deleteConnection,
  receiveWebhook,
  getSyncStatus,
  triggerSync,
} from '../controllers/githubSyncController.js';

const router = Router({ mergeParams: true });

// ── Public webhook receiver ──────────────────────────────────────────────────
// Must be registered BEFORE auth middleware.
// Uses raw body parsing to allow HMAC-SHA256 signature verification.
// The upstream express setup must expose req.rawBody for this route.
router.post('/github-sync/webhook', receiveWebhook);

// ── Authenticated connection management ──────────────────────────────────────

router.get(
  '/:communityId/github-sync/connections',
  requireAuth,
  requireCommunityAdmin,
  listConnections
);

router.post(
  '/:communityId/github-sync/connections',
  requireAuth,
  requireCommunityAdmin,
  createConnection
);

router.delete(
  '/:communityId/github-sync/connections/:id',
  requireAuth,
  requireCommunityAdmin,
  deleteConnection
);

// ── Ticket sync status + manual trigger ─────────────────────────────────────

router.get(
  '/:communityId/github-sync/ticket/:ticketId/sync-status',
  requireAuth,
  requireCommunityAdmin,
  getSyncStatus
);

router.post(
  '/:communityId/github-sync/ticket/:ticketId/sync',
  requireAuth,
  requireCommunityAdmin,
  triggerSync
);

export default router;
