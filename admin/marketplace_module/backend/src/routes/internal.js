import { Router } from 'express';
import * as routerIntegrationController from '../controllers/routerIntegrationController.js';
import { requireServiceAuth } from '../middleware/auth.js';

const router = Router();
router.use(requireServiceAuth);

router.get('/commands/:communityId', routerIntegrationController.getCommunityCommands);
router.post('/execute/:moduleId', routerIntegrationController.executeModuleCommand);

export default router;
