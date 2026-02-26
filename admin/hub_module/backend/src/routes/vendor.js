/**
 * Vendor Module Submission Routes
 */
import { Router } from 'express';
import * as vendorSubmissionController from '../controllers/vendorSubmissionController.js';
import * as vendorRequestController from '../controllers/vendorRequestController.js';
import { requireAuth, requireSuperAdmin } from '../middleware/auth.js';

const router = Router();

/**
 * Public Vendor Routes (no authentication required for initial submission)
 */

// Submit a new vendor module
router.post('/vendor/submit', vendorSubmissionController.submitVendorModule);

// Get submission status (public - requires email verification)
router.get('/vendor/submissions/:submissionId', vendorSubmissionController.getSubmissionStatus);

// Get published modules (public listing)
router.get('/vendor/modules', vendorSubmissionController.getPublishedModules);

/**
 * Vendor Request Routes (authenticated users)
 */

// Submit a vendor role request (authenticated)
router.post('/vendor/request', requireAuth, vendorRequestController.submitVendorRequest);

// Get vendor request status (authenticated)
router.get('/vendor/request/status', requireAuth, vendorRequestController.getVendorRequestStatus);

/**
 * Admin Routes (superadmin authentication required)
 */

// All admin routes require super admin
router.use('/admin/vendor', requireAuth);
router.use('/admin/vendor', requireSuperAdmin);

// Get all submissions for review
router.get('/admin/vendor/submissions', vendorSubmissionController.getSubmissionsForReview);

// Get detailed submission information
router.get('/admin/vendor/submissions/:submissionId', vendorSubmissionController.getSubmissionDetails);

// Approve a submission
router.post('/admin/vendor/submissions/:submissionId/approve', vendorSubmissionController.approveSubmission);

// Reject a submission
router.post('/admin/vendor/submissions/:submissionId/reject', vendorSubmissionController.rejectSubmission);

// Request more information
router.post('/admin/vendor/submissions/:submissionId/request-info', vendorSubmissionController.requestMoreInfo);

// Publish an approved module
router.post('/admin/vendor/submissions/:submissionId/publish', vendorSubmissionController.publishModule);

/**
 * Vendor Request Management Routes (superadmin only)
 */

// Get all pending vendor requests
router.get('/admin/vendor/requests', vendorRequestController.getPendingVendorRequests);

// Approve a vendor request
router.post('/admin/vendor/requests/:requestId/approve', vendorRequestController.approveVendorRequest);

// Reject a vendor request
router.post('/admin/vendor/requests/:requestId/reject', vendorRequestController.rejectVendorRequest);

export default router;
