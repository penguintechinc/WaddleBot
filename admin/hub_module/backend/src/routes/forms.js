/**
 * Community Forms Routes - Form management for community engagement
 */
import { Router } from 'express';
import * as formsController from '../controllers/formsController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';

const router = Router({ mergeParams: true });

// All routes require authentication and community admin role
router.use(requireAuth);

/**
 * Form Management
 */

// Get all forms for a community
router.get(
  '/:communityId/forms',
  requireCommunityAdmin,
  formsController.getForms
);

// Get a specific form
router.get(
  '/:communityId/forms/:formId',
  requireCommunityAdmin,
  validators.id('formId'),
  validateRequest,
  formsController.getForm
);

// Create a new form
router.post(
  '/:communityId/forms',
  requireCommunityAdmin,
  validators.text('title', { min: 1, max: 255 }),
  validators.text('description', { min: 0, max: 2000, optional: true }),
  validators.array('fields', { min: 1 }),
  validators.text('view_visibility', { pattern: /^(public|registered|community|admins)$/, optional: true }),
  validators.text('submit_visibility', { pattern: /^(public|registered|community|admins)$/, optional: true }),
  validators.text('results_visibility', { pattern: /^(community|registered|submitter_and_admins|admins)$/, optional: true }),
  validators.boolean('allow_anonymous', { optional: true }),
  validators.boolean('submit_once_per_user', { optional: true }),
  validateRequest,
  formsController.createForm
);

// Delete a form
router.delete(
  '/:communityId/forms/:formId',
  requireCommunityAdmin,
  validators.id('formId'),
  validateRequest,
  formsController.deleteForm
);

/**
 * Form Submissions
 */

// Get submissions for a form
router.get(
  '/:communityId/forms/:formId/submissions',
  requireCommunityAdmin,
  validators.id('formId'),
  validateRequest,
  formsController.getFormSubmissions
);

export default router;
