/**
 * Marketplace Routes - Module marketplace for community admins
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import * as marketplaceController from '../controllers/marketplaceController.js';

const router = Router();

// All marketplace routes require authentication and community admin role
router.use(requireAuth);

// Browse modules
router.get(
  '/:communityId/marketplace/modules',
  requireCommunityAdmin,
  marketplaceController.browseModules
);

// Get module details
router.get(
  '/:communityId/marketplace/modules/:id',
  requireCommunityAdmin,
  marketplaceController.getModuleDetails
);

// Install module
router.post(
  '/:communityId/marketplace/modules/:id/install',
  requireCommunityAdmin,
  marketplaceController.installModule
);

// Uninstall module
router.delete(
  '/:communityId/marketplace/modules/:id',
  requireCommunityAdmin,
  marketplaceController.uninstallModule
);

// Configure module
router.put(
  '/:communityId/marketplace/modules/:id/config',
  requireCommunityAdmin,
  marketplaceController.configureModule
);

// Add review
router.post(
  '/:communityId/marketplace/modules/:id/review',
  requireCommunityAdmin,
  marketplaceController.addReview
);

export default router;
