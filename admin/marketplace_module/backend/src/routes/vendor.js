/**
 * Vendor Routes — vendor profile, module management, submission workflow, and discount codes
 */
import { Router } from 'express';
import * as vendorController from '../controllers/vendorController.js';
import * as discountCodeController from '../controllers/discountCodeController.js';
import * as vendorAnalyticsController from '../controllers/vendorAnalyticsController.js';
import { requireAuth } from '../middleware/auth.js';

const router = Router();
router.use(requireAuth);

router.get('/dashboard', vendorController.getVendorDashboard);
router.get('/profile', vendorController.getVendorProfile);
router.post('/profile', vendorController.createVendorProfile);
router.put('/profile', vendorController.updateVendorProfile);

// Comprehensive analytics routes — registered before /analytics/overview to prevent path conflicts
router.get('/analytics/sales', vendorAnalyticsController.getSalesMetrics);
router.get('/analytics/installs', vendorAnalyticsController.getInstallTimeSeries);
router.get('/analytics/api-usage', vendorAnalyticsController.getApiUsageMetrics);
router.get('/analytics/discount-codes', vendorAnalyticsController.getDiscountCodePerformance);
router.get('/analytics/communities', vendorAnalyticsController.getCommunityDrilldown);
router.get('/analytics/export', vendorAnalyticsController.exportCsv);
router.get('/analytics/overview', vendorController.getVendorAnalyticsOverview);
router.get('/modules', vendorController.getVendorModules);
router.post('/modules', vendorController.createVendorModule);
router.put('/modules/:id', vendorController.updateVendorModule);
router.post('/modules/:id/submit', vendorController.submitModuleForReview);
router.get('/request', vendorController.getVendorRequest);
router.post('/request', vendorController.createVendorRequest);

// Discount code routes — validate/redeem must be registered before /:id to avoid param collision
router.post('/discount-codes/validate', discountCodeController.validateCode);
router.post('/discount-codes/redeem', discountCodeController.redeemCode);
router.get('/discount-codes', discountCodeController.listDiscountCodes);
router.post('/discount-codes', discountCodeController.createDiscountCode);
router.put('/discount-codes/:id', discountCodeController.updateDiscountCode);
router.delete('/discount-codes/:id', discountCodeController.deleteDiscountCode);

export default router;
