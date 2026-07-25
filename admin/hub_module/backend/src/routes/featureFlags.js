/**
 * Feature Flag Routes - community admin access.
 *
 * Mounted under the same /admin prefix and protected exactly like the other
 * community-admin routes (admin.js): requireAuth on the router, then
 * requireCommunityAdmin per route (which enforces the :communityId scope).
 * community_id is always taken from the URL param, never the body.
 */
import { Router } from 'express';
import { body, param } from 'express-validator';
import * as featureFlagController from '../controllers/featureFlagController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { validateRequest } from '../middleware/validation.js';
import { PLATFORM_ALLOWLIST } from '../services/featureFlagService.js';

const router = Router();

router.use(requireAuth);

// Validation chains for create/update override bodies.
const flagKeyValidator = body('flag_key')
  .isString()
  .bail()
  .isLength({ min: 1, max: 100 })
  .withMessage('flag_key must be 1-100 characters')
  .bail()
  .matches(/^[a-z0-9_.-]+$/)
  .withMessage('flag_key may only contain lowercase letters, digits, dot, dash and underscore');

const platformValidator = body('platform')
  .optional({ nullable: true })
  .custom((v) => v === null || v === '' || v === 'all' || PLATFORM_ALLOWLIST.includes(v))
  .withMessage(`platform must be null/all or one of: ${PLATFORM_ALLOWLIST.join(', ')}`);

const rolloutValidator = body('rollout_pct')
  .optional()
  .isInt({ min: 0, max: 100 })
  .withMessage('rollout_pct must be an integer between 0 and 100');

const enabledValidator = body('is_enabled').optional().isBoolean().withMessage('is_enabled must be a boolean');
const descriptionValidator = body('description').optional({ nullable: true }).isString().isLength({ max: 5000 });

// List merged flag view for this community
router.get('/:communityId/feature-flags', requireCommunityAdmin, featureFlagController.listCommunityFlags);

// Create a community-scoped override
router.post(
  '/:communityId/feature-flags',
  requireCommunityAdmin,
  flagKeyValidator,
  platformValidator,
  rolloutValidator,
  enabledValidator,
  descriptionValidator,
  validateRequest,
  featureFlagController.createCommunityOverride
);

// Update a community-scoped override
router.put(
  '/:communityId/feature-flags/:id',
  requireCommunityAdmin,
  param('id').isInt({ min: 1 }),
  rolloutValidator,
  enabledValidator,
  descriptionValidator,
  validateRequest,
  featureFlagController.updateCommunityOverride
);

// Delete a community-scoped override
router.delete(
  '/:communityId/feature-flags/:id',
  requireCommunityAdmin,
  param('id').isInt({ min: 1 }),
  validateRequest,
  featureFlagController.deleteCommunityOverride
);

export default router;
