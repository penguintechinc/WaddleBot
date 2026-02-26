/**
 * Inventory (Quartermaster) Routes
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import {
  listItems,
  createItem,
  updateItem,
  deleteItem,
  addStock,
  removeStock,
  listAllCheckouts,
  getSummary,
  getAuditLog,
  listAvailable,
  checkoutItem,
  checkinItem,
  getMyCheckouts
} from '../controllers/inventoryController.js';

const router = Router({ mergeParams: true });

// ── Admin Routes ───────────────────────────────────────────────

router.get('/:communityId/inventory/items', requireAuth, requireCommunityAdmin, listItems);
router.post('/:communityId/inventory/items', requireAuth, requireCommunityAdmin, createItem);
router.put('/:communityId/inventory/items/:itemId', requireAuth, requireCommunityAdmin, updateItem);
router.delete('/:communityId/inventory/items/:itemId', requireAuth, requireCommunityAdmin, deleteItem);

router.post('/:communityId/inventory/items/:itemId/stock/add', requireAuth, requireCommunityAdmin, addStock);
router.post('/:communityId/inventory/items/:itemId/stock/remove', requireAuth, requireCommunityAdmin, removeStock);

router.get('/:communityId/inventory/checkouts', requireAuth, requireCommunityAdmin, listAllCheckouts);
router.get('/:communityId/inventory/summary', requireAuth, requireCommunityAdmin, getSummary);
router.get('/:communityId/inventory/log', requireAuth, requireCommunityAdmin, getAuditLog);

// ── Member Routes ──────────────────────────────────────────────

router.get('/:communityId/inventory/available', requireAuth, listAvailable);
router.post('/:communityId/inventory/checkout', requireAuth, checkoutItem);
router.post('/:communityId/inventory/checkin', requireAuth, checkinItem);
router.get('/:communityId/inventory/my-items', requireAuth, getMyCheckouts);

export default router;
