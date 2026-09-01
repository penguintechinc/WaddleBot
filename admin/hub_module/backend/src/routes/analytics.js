/**
 * Analytics Routes
 * Mounted at /api/v1/analytics by routes/index.js
 *
 * Scenarios:
 * 1. Self stats — any authenticated user
 * 2. Community admin views member — requireCommunityAdmin
 * 3. Superadmin views any user — requireSuperAdmin
 * 4. Platform overview — requireAnalyticsConsumer (superadmin passes too)
 */
import { Router } from 'express';
import * as analyticsController from '../controllers/analyticsController.js';
import { requireAuth, requireSuperAdmin, requireCommunityAdmin, requireAnalyticsConsumer } from '../middleware/auth.js';

const router = Router();

// Scenario 1: Self stats (any authenticated user)
router.get('/me/stats', requireAuth, analyticsController.getUserSelfStats);
router.get('/me/reputation', requireAuth, analyticsController.getUserReputation);

// Scenario 2: Community admin views member
router.get('/community/:communityId/members/:userId/stats', requireAuth, requireCommunityAdmin, analyticsController.getUserCommunityStats);
router.get('/community/:communityId/members/:userId/reputation', requireAuth, requireCommunityAdmin, analyticsController.getUserReputation);

// Scenario 3+4: Platform overview (analyticsConsumer OR superadmin)
router.get('/platform/overview', requireAuth, requireAnalyticsConsumer, analyticsController.getPlatformOverview);
router.get('/platform/reputation', requireAuth, requireAnalyticsConsumer, analyticsController.getReputationDistribution);
router.get('/platform/growth', requireAuth, requireAnalyticsConsumer, analyticsController.getGrowthTrends);
router.get('/platform/activity', requireAuth, requireAnalyticsConsumer, analyticsController.getActivityBreakdown);
router.get('/platform/community-health', requireAuth, requireAnalyticsConsumer, analyticsController.getCommunityHealthSummaries);

// Scenario 3: Superadmin views any user
router.get('/admin/users/:userId/stats', requireAuth, requireSuperAdmin, analyticsController.getUserSelfStats);
router.get('/admin/users/:userId/reputation', requireAuth, requireSuperAdmin, analyticsController.getUserReputation);

export default router;
