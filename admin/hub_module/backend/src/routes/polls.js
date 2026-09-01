/**
 * Community Polls Routes - Poll management for community engagement
 */
import { Router } from 'express';
import * as pollsController from '../controllers/pollsController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';

const router = Router({ mergeParams: true });

// All routes require authentication and community admin role
router.use(requireAuth);

/**
 * Poll Management
 */

// Get all polls for a community
router.get(
  '/:communityId/polls',
  requireCommunityAdmin,
  pollsController.getPolls
);

// Get a specific poll with results
router.get(
  '/:communityId/polls/:pollId',
  requireCommunityAdmin,
  validators.id('pollId'),
  validateRequest,
  pollsController.getPoll
);

// Create a new poll
router.post(
  '/:communityId/polls',
  requireCommunityAdmin,
  validators.text('title', { min: 1, max: 255 }),
  validators.text('description', { min: 0, max: 2000, optional: true }),
  validators.array('options', { min: 2 }),
  validators.text('view_visibility', { pattern: /^(public|registered|community|admins)$/, optional: true }),
  validators.text('submit_visibility', { pattern: /^(public|registered|community|admins)$/, optional: true }),
  validators.boolean('allow_multiple_choices', { optional: true }),
  validators.integer('max_choices', { min: 1, max: 10, optional: true }),
  validateRequest,
  pollsController.createPoll
);

// Delete a poll
router.delete(
  '/:communityId/polls/:pollId',
  requireCommunityAdmin,
  validators.id('pollId'),
  validateRequest,
  pollsController.deletePoll
);

export default router;
