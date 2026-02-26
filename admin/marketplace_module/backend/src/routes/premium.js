import { Router } from 'express';
import * as premiumController from '../controllers/premiumController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';

const router = Router();

router.get('/pricing', premiumController.getPricing);
router.get('/status/:communityId', requireAuth, requireCommunityAdmin, premiumController.getSubscriptionStatus);
router.post('/subscribe', requireAuth, requireCommunityAdmin, premiumController.subscribePremium);
router.post('/cancel', requireAuth, requireCommunityAdmin, premiumController.cancelPremium);

export default router;
