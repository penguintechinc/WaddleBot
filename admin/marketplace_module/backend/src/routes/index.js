/**
 * Route Aggregator
 * Combines all API routes under /api/v1
 */
import { Router } from 'express';
import moduleRoutes from './modules.js';
import subscriptionRoutes from './subscriptions.js';
import catalogRoutes from './catalog.js';
import installationRoutes from './installations.js';
import vendorRoutes from './vendor.js';
import adminReviewRoutes from './adminReview.js';
import premiumRoutes from './premium.js';
import internalRoutes from './internal.js';

import paymentRoutes from './payments.js';
import webhookRoutes from './webhooks.js';

const router = Router();

// Legacy module routes (hub_modules focused)
router.use('/modules', moduleRoutes);
router.use('/communities', subscriptionRoutes);

// Unified catalog (public + optional auth)
router.use('/catalog', catalogRoutes);

// Community installation management
router.use('/communities', installationRoutes);

// Vendor self-service
router.use('/vendor', vendorRoutes);

// Global admin review and settings
router.use('/admin/marketplace', adminReviewRoutes);

// Community premium subscriptions
router.use('/premium', premiumRoutes);

// Payment processing (existing)
router.use('/payments', paymentRoutes);

// Payment webhooks (no auth, provider-verified)
router.use('/webhooks', webhookRoutes);

// Internal service-to-service API (router module)
router.use('/internal', internalRoutes);

export default router;
