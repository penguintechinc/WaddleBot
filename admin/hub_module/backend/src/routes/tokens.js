/**
 * PAT/CAT Token Routes
 * PAT = Personal Access Token (wdl_u_*): one per user, acts as that user
 * CAT = Community Access Token (wdl_c_*): service/bot credential for a community
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import {
  getPAT,
  createPAT,
  revokePAT,
  listCATs,
  createCAT,
  revokeCAT,
  listScopes
} from '../controllers/tokenController.js';

const router = Router({ mergeParams: true });

// ── User PAT routes (require session auth) ─────────────────────

// Scope catalog — useful for the PAT scope-ceiling picker
router.get('/user/tokens/scopes', requireAuth, listScopes);

// Current user's PAT
router.get('/user/tokens/pat', requireAuth, getPAT);
router.post('/user/tokens/pat', requireAuth, createPAT);
router.delete('/user/tokens/pat', requireAuth, revokePAT);

// ── Community CAT routes (require community admin) ─────────────

router.get('/:communityId/tokens/scopes', requireAuth, requireCommunityAdmin, listScopes);
router.get('/:communityId/tokens/cats', requireAuth, requireCommunityAdmin, listCATs);
router.post('/:communityId/tokens/cats', requireAuth, requireCommunityAdmin, createCAT);
router.delete('/:communityId/tokens/cats/:tokenId', requireAuth, requireCommunityAdmin, revokeCAT);

export default router;
