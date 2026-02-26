import { Router } from 'express';
import { requireAuth, requireTenantAdmin, resolveTenant } from '../middleware/auth.js';
import * as tenantController from '../controllers/tenantController.js';

const router = Router({ mergeParams: true });

// All routes require auth + tenant admin
router.use(requireAuth);

router.get('/:tenantSlug', resolveTenant, requireTenantAdmin, tenantController.getTenant);
router.put('/:tenantSlug', resolveTenant, requireTenantAdmin, tenantController.updateTenant);
router.get('/:tenantSlug/settings', resolveTenant, requireTenantAdmin, tenantController.getTenantSettings);
router.put('/:tenantSlug/settings', resolveTenant, requireTenantAdmin, tenantController.updateTenantSettings);
router.get('/:tenantSlug/communities', resolveTenant, requireTenantAdmin, tenantController.getTenantCommunities);
router.get('/:tenantSlug/modules', resolveTenant, requireTenantAdmin, tenantController.getTenantModules);
router.put('/:tenantSlug/modules', resolveTenant, requireTenantAdmin, tenantController.updateTenantModules);
router.get('/:tenantSlug/admins', resolveTenant, requireTenantAdmin, tenantController.getTenantAdmins);
router.post('/:tenantSlug/admins', resolveTenant, requireTenantAdmin, tenantController.addTenantAdmin);
router.delete('/:tenantSlug/admins/:userId', resolveTenant, requireTenantAdmin, tenantController.removeTenantAdmin);

export default router;
