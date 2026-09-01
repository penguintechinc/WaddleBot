/**
 * Raffle Customization Routes
 * Provides community admins the ability to configure custom sounds and
 * message templates for raffle and giveaway events.
 *
 * All routes are mounted under /admin (see routes/index.js).
 * Full path: /api/v1/admin/:communityId/raffle-customization/...
 */
import { Router } from 'express';
import multer from 'multer';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import {
  getRaffleCustomization,
  upsertRaffleCustomization,
  deleteRaffleCustomization,
  uploadRaffleSound,
} from '../controllers/raffleCustomizationController.js';

const router = Router();

// Use memory storage — controller writes to disk after validation
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 2 * 1024 * 1024 }, // 2MB hard limit (multer layer)
});

router.use(requireAuth);

// GET /:communityId/raffle-customization
// List all custom sounds/messages for a community
router.get(
  '/:communityId/raffle-customization',
  requireCommunityAdmin,
  getRaffleCustomization
);

// PUT /:communityId/raffle-customization/:eventType
// Upsert message template and/or active flag for an event type
router.put(
  '/:communityId/raffle-customization/:eventType',
  requireCommunityAdmin,
  upsertRaffleCustomization
);

// DELETE /:communityId/raffle-customization/:eventType
// Reset event type to defaults (removes row and sound file)
router.delete(
  '/:communityId/raffle-customization/:eventType',
  requireCommunityAdmin,
  deleteRaffleCustomization
);

// POST /:communityId/raffle-customization/:eventType/upload
// Upload a sound file (mp3/ogg/wav, max 2MB)
router.post(
  '/:communityId/raffle-customization/:eventType/upload',
  requireCommunityAdmin,
  upload.single('sound'),
  uploadRaffleSound
);

export default router;
