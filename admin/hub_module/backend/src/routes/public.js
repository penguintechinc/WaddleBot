/**
 * Public Routes - No authentication required
 */
import { Router } from 'express';
import * as publicController from '../controllers/publicController.js';
import * as profileController from '../controllers/profileController.js';
import * as communityProfileController from '../controllers/communityProfileController.js';
import { optionalAuth } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';

const router = Router();

// Platform statistics
router.get('/stats', publicController.getStats);

// Spotlighted communities (top active, excludes support type)
router.get('/communities/spotlighted', publicController.getSpotlightedCommunities);

// Communities
router.get('/communities',
  validators.pagination(),
  validateRequest,
  publicController.getCommunities
);
router.get('/communities/:id', publicController.getCommunity);
router.get('/communities/:id/profile', optionalAuth, communityProfileController.getCommunityProfile);

// Live streams
router.get('/live',
  validators.pagination(),
  validateRequest,
  publicController.getLiveStreams
);
router.get('/live/:entityId', publicController.getStreamDetails);

// Signup settings (for login page to determine if signup is available)
router.get('/signup-settings', publicController.getSignupSettings);

// User profiles (optional auth to check visibility permissions)
router.get('/users/:userId/profile', optionalAuth, profileController.getPublicProfile);

// Public marketplace (browse modules without auth)
router.get('/marketplace/modules',
  validators.pagination(),
  validateRequest,
  publicController.getMarketplaceModules
);
router.get('/marketplace/modules/:id', publicController.getMarketplaceModule);
router.get('/marketplace/categories', publicController.getMarketplaceCategories);

// Global announcement banner (public, no auth)
router.get('/banner', publicController.getBanner);

export default router;
