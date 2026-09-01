/**
 * Installation Routes — community module management
 */
import { Router } from 'express';
import * as installationController from '../controllers/installationController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';

const router = Router();
router.use(requireAuth);

router.get('/:communityId/installed', requireCommunityAdmin, installationController.getInstalledModules);
router.post('/:communityId/install', requireCommunityAdmin, installationController.installModule);
router.delete('/:communityId/install/:moduleId', requireCommunityAdmin, installationController.uninstallModule);
router.put('/:communityId/install/:moduleId', requireCommunityAdmin, installationController.toggleModule);

export default router;
