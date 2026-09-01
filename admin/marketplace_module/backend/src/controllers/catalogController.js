/**
 * Catalog Controller — Unified module browsing endpoints
 */
import * as catalogService from '../services/catalogService.js';

/**
 * GET /catalog
 * Browse unified module catalog with search, filters, and pagination.
 */
export async function browseCatalog(req, res, next) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const search = req.query.search || '';
    const category = req.query.category || null;
    const pricingType = req.query.pricingType || null;
    const source = req.query.source || null;
    const communityId = req.query.communityId
      ? parseInt(req.query.communityId, 10)
      : null;

    const result = await catalogService.getCatalog({
      page,
      limit,
      search,
      category,
      pricingType,
      source,
      communityId,
    });

    res.json({ success: true, ...result });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /catalog/categories
 * List distinct categories with module counts.
 */
export async function getCategories(req, res, next) {
  try {
    const categories = await catalogService.getCategories();
    res.json({ success: true, categories });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /catalog/featured
 * Get featured / top modules.
 */
export async function getFeatured(req, res, next) {
  try {
    const communityId = req.query.communityId
      ? parseInt(req.query.communityId, 10)
      : null;
    const modules = await catalogService.getFeatured(communityId);
    res.json({ success: true, modules });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /catalog/:source/:id
 * Get single catalog entry detail.
 */
export async function getCatalogEntry(req, res, next) {
  try {
    const { source, id } = req.params;
    const sourceId = parseInt(id, 10);
    const communityId = req.query.communityId
      ? parseInt(req.query.communityId, 10)
      : null;

    const entry = await catalogService.getCatalogEntry(source, sourceId, communityId);
    if (!entry) {
      return res.status(404).json({ success: false, error: { code: 'NOT_FOUND', message: 'Module not found' } });
    }

    res.json({ success: true, module: entry });
  } catch (err) {
    next(err);
  }
}

export default {
  browseCatalog,
  getCategories,
  getFeatured,
  getCatalogEntry,
};
