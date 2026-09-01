/**
 * Vendor Controller — vendor profile, module CRUD, and submission workflow
 */
import * as vendorService from '../services/vendorService.js';

/**
 * GET /vendor/profile
 * Returns the authenticated user's vendor profile.
 */
export async function getVendorProfile(req, res, next) {
  try {
    const seller = await vendorService.getVendorProfile(req.user.id);
    res.json({ success: true, seller });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/dashboard
 * Returns enhanced dashboard data for the authenticated vendor.
 */
export async function getVendorDashboard(req, res, next) {
  try {
    const data = await vendorService.getVendorDashboard(req.user.id);
    res.json({ success: true, ...data });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /vendor/profile
 * Updates the authenticated user's vendor profile.
 */
export async function updateVendorProfile(req, res, next) {
  try {
    const { displayName, description, websiteUrl, payoutMethod } = req.body;

    if (!displayName || typeof displayName !== 'string' || displayName.trim() === '') {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'displayName is required' },
      });
    }

    const URL_RE = /^https?:\/\/.+/i;
    if (websiteUrl && !URL_RE.test(websiteUrl)) {
      return res.status(400).json({
        success: false,
        error: { code: 'VALIDATION_ERROR', message: 'websiteUrl must be a valid URL starting with http:// or https://' },
      });
    }

    const VALID_PAYOUT_METHODS = ['stripe', 'paypal', 'bank_transfer'];
    if (payoutMethod && !VALID_PAYOUT_METHODS.includes(payoutMethod)) {
      return res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: `payoutMethod must be one of: ${VALID_PAYOUT_METHODS.join(', ')}`,
        },
      });
    }

    const seller = await vendorService.updateVendorProfile(req.user.id, {
      displayName: displayName.trim(),
      description,
      websiteUrl,
      payoutMethod,
    });
    res.json({ success: true, seller });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/analytics/overview
 * Returns a basic analytics summary for the authenticated vendor's modules.
 */
export async function getVendorAnalyticsOverview(req, res, next) {
  try {
    const analytics = await vendorService.getVendorAnalyticsOverview(req.user.id);
    res.json({ success: true, analytics });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/profile
 * Creates a vendor profile for the authenticated user.
 */
export async function createVendorProfile(req, res, next) {
  try {
    const seller = await vendorService.createVendorProfile(req.user.id, req.body);
    res.status(201).json({ success: true, seller });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/modules
 * Returns paginated modules owned by the authenticated vendor.
 */
export async function getVendorModules(req, res, next) {
  try {
    const { page, limit } = req.query;
    const { modules, pagination } = await vendorService.getVendorModules(req.user.id, {
      page: page ? parseInt(page, 10) : 1,
      limit: limit ? parseInt(limit, 10) : 25,
    });
    res.json({ success: true, modules, pagination });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/modules
 * Creates a new marketplace module for the authenticated vendor.
 */
export async function createVendorModule(req, res, next) {
  try {
    const module = await vendorService.createVendorModule(req.user.id, req.body);
    res.status(201).json({ success: true, module });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /vendor/modules/:id
 * Updates an existing vendor-owned module.
 */
export async function updateVendorModule(req, res, next) {
  try {
    const moduleId = parseInt(req.params.id, 10);
    await vendorService.updateVendorModule(req.user.id, moduleId, req.body);
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/modules/:id/submit
 * Submits a vendor module for marketplace review.
 */
export async function submitModuleForReview(req, res, next) {
  try {
    const moduleId = parseInt(req.params.id, 10);
    const { changesDescription } = req.body;
    const { submissionId } = await vendorService.submitModuleForReview(
      req.user.id,
      moduleId,
      changesDescription
    );
    res.json({ success: true, submissionId, message: 'Module submitted for review' });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/request
 * Returns the authenticated user's most recent vendor role request.
 */
export async function getVendorRequest(req, res, next) {
  try {
    const request = await vendorService.getVendorRequest(req.user.id);
    res.json({ success: true, request });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /vendor/request
 * Submits a new vendor role request for the authenticated user.
 */
export async function createVendorRequest(req, res, next) {
  try {
    const request = await vendorService.createVendorRequest(req.user.id, req.body);
    res.status(201).json({ success: true, request });
  } catch (err) {
    next(err);
  }
}

export default {
  getVendorDashboard,
  getVendorProfile,
  createVendorProfile,
  updateVendorProfile,
  getVendorModules,
  createVendorModule,
  updateVendorModule,
  submitModuleForReview,
  getVendorRequest,
  createVendorRequest,
  getVendorAnalyticsOverview,
};
