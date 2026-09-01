import { Router } from 'express';
import * as adminReviewController from '../controllers/adminReviewController.js';
import { requireAuth, requireSuperAdmin } from '../middleware/auth.js';

const router = Router();
router.use(requireAuth, requireSuperAdmin);

router.get('/vendor-requests', adminReviewController.getVendorRequests);
router.post('/vendor-requests/:id/approve', adminReviewController.approveVendorRequest);
router.post('/vendor-requests/:id/reject', adminReviewController.rejectVendorRequest);
router.get('/submissions', adminReviewController.getSubmissions);
router.post('/submissions/:id/approve', adminReviewController.approveSubmission);
router.post('/submissions/:id/reject', adminReviewController.rejectSubmission);
router.get('/settings', adminReviewController.getMarketplaceSettings);
router.put('/settings', adminReviewController.updateMarketplaceSettings);

export default router;
