/**
 * Vendor Routes — vendor profile, module management, and submission workflow
 */
import { Router } from 'express';
import * as vendorController from '../controllers/vendorController.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();
router.use(requireAuth);

router.get('/dashboard', vendorController.getVendorDashboard);
router.get('/profile', vendorController.getVendorProfile);
router.post('/profile', vendorController.createVendorProfile);
router.put('/profile', vendorController.updateVendorProfile);
router.get('/analytics/overview', vendorController.getVendorAnalyticsOverview);
router.get('/modules', vendorController.getVendorModules);
router.post('/modules', vendorController.createVendorModule);
router.put('/modules/:id', vendorController.updateVendorModule);
router.post('/modules/:id/submit', vendorController.submitModuleForReview);
router.get('/request', vendorController.getVendorRequest);
router.post('/request', vendorController.createVendorRequest);

export default router;
