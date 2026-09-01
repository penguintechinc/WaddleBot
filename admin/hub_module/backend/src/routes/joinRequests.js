/**
 * Join Request Routes
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import * as joinRequestController from '../controllers/joinRequestController.js';

const router = Router({ mergeParams: true });

// Member routes
router.post('/:communityId/join-requests', requireAuth, joinRequestController.submitRequest);
router.get('/:communityId/join-requests/mine', requireAuth, joinRequestController.getMyRequest);

// Admin routes
router.get('/:communityId/join-requests', requireCommunityAdmin, joinRequestController.listRequests);
router.put('/:communityId/join-requests/:requestId/approve', requireCommunityAdmin, joinRequestController.approveRequest);
router.put('/:communityId/join-requests/:requestId/reject', requireCommunityAdmin, joinRequestController.rejectRequest);

export default router;
