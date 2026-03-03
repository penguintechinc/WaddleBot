/**
 * Support Ticket System Routes
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  listTickets,
  getTicket,
  createTicket,
  updateTicketStatus,
  assignTicket,
  updateTicketPriority,
  addComment,
  getMyTickets,
  getTicketStats
} from '../controllers/supportController.js';

const router = Router({ mergeParams: true });

// ── Admin Routes ──────────────────────────────────────────────

// Categories
router.get('/:communityId/support/categories', requireAuth, getCategories);
router.post('/:communityId/support/categories', requireAuth, requireCommunityAdmin, createCategory);
router.put('/:communityId/support/categories/:categoryId', requireAuth, requireCommunityAdmin, updateCategory);
router.delete('/:communityId/support/categories/:categoryId', requireAuth, requireCommunityAdmin, deleteCategory);

// Admin ticket management
router.get('/:communityId/support/tickets', requireAuth, requireCommunityAdmin, (req, res, next) => {
  req.isAdmin = true;
  next();
}, listTickets);

router.get('/:communityId/support/tickets/:ticketId', requireAuth, requireCommunityAdmin, (req, res, next) => {
  req.isAdmin = true;
  next();
}, getTicket);

router.put('/:communityId/support/tickets/:ticketId/status',
  requireAuth, requireCommunityAdmin,
  validators.text('status', { pattern: /^(open|in_progress|waiting|resolved|closed)$/ }),
  validateRequest,
  updateTicketStatus
);

router.put('/:communityId/support/tickets/:ticketId/assign', requireAuth, requireCommunityAdmin, assignTicket);

router.put('/:communityId/support/tickets/:ticketId/priority',
  requireAuth, requireCommunityAdmin,
  validators.text('priority', { pattern: /^(low|medium|high|urgent)$/ }),
  validateRequest,
  updateTicketPriority
);

router.post('/:communityId/support/tickets/:ticketId/comments', requireAuth, requireCommunityAdmin, (req, res, next) => {
  req.isAdmin = true;
  next();
}, addComment);

// Stats
router.get('/:communityId/support/stats', requireAuth, requireCommunityAdmin, getTicketStats);

// ── Member Routes ─────────────────────────────────────────────

// Submit a ticket
router.post('/:communityId/support/submit',
  requireAuth,
  validators.text('subject', { min: 1, max: 500 }),
  validateRequest,
  createTicket
);

// My tickets
router.get('/:communityId/support/my-tickets', requireAuth, getMyTickets);

router.get('/:communityId/support/my-tickets/:ticketId', requireAuth, (req, res, next) => {
  req.isAdmin = false;
  next();
}, getTicket);

router.post('/:communityId/support/my-tickets/:ticketId/comments', requireAuth, (req, res, next) => {
  req.body.is_internal = false;
  next();
}, addComment);

export default router;
