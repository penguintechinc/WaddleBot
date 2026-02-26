/**
 * Catalog Routes — Public + optional-auth browsing
 */
import { Router } from 'express';
import * as catalogController from '../controllers/catalogController.js';
import { optionalAuth } from '../middleware/auth.js';

const router = Router();

// All catalog routes use optional auth (public browsing, enriched if logged in)
router.use(optionalAuth);

// GET /catalog — paginated browsing with search & filters
router.get('/', catalogController.browseCatalog);

// GET /catalog/categories — list distinct categories
router.get('/categories', catalogController.getCategories);

// GET /catalog/featured — top/featured modules
router.get('/featured', catalogController.getFeatured);

// GET /catalog/:source/:id — single module detail
router.get('/:source/:id', catalogController.getCatalogEntry);

export default router;
