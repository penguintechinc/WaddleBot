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
  getVendorProfile,
  createVendorProfile,
  getVendorModules,
  createVendorModule,
  updateVendorModule,
  submitModuleForReview,
  getVendorRequest,
  createVendorRequest,
};
