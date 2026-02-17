/**
 * Super Admin Routes - Global admin features for managing all communities
 */
import { Router } from 'express';
import * as superadminController from '../controllers/superadminController.js';
import PlatformConfigController from '../controllers/platformConfigController.js';
import * as kongController from '../controllers/kongController.js';
import * as userManagementController from '../controllers/userManagementController.js';
import { requireAuth, requireSuperAdmin } from '../middleware/auth.js';
import { validators, validationRules, validateRequest } from '../middleware/validation.js';

const router = Router();

// All routes require super admin authentication
router.use(requireAuth);
router.use(requireSuperAdmin);

// Dashboard stats
router.get('/dashboard', superadminController.getDashboardStats);

// Community management
router.get('/communities', superadminController.listCommunities);
router.get('/communities/:id', superadminController.getCommunity);
router.post('/communities',
  validationRules.createCommunity,
  validateRequest,
  superadminController.createCommunity
);
router.put('/communities/:id',
  validators.text('name', { min: 3, max: 100 }),
  validators.text('display_name', { min: 3, max: 255 }),
  validators.text('description', { min: 0, max: 5000 }),
  validators.boolean('is_public'),
  validators.boolean('allow_join_requests'),
  validateRequest,
  superadminController.updateCommunity
);
router.delete('/communities/:id', superadminController.deleteCommunity);
router.post('/communities/:id/reassign',
  validators.integer('new_owner_id', { min: 1 }),
  validateRequest,
  superadminController.reassignOwner
);

// Module registry management
router.get('/marketplace/modules', superadminController.getAllModules);
router.post('/marketplace/modules',
  validators.text('name', { min: 3, max: 100 }),
  validators.text('description', { min: 10, max: 5000 }),
  validators.text('version', { min: 1, max: 20 }),
  validators.text('author', { min: 1, max: 100 }),
  validators.url('repository_url'),
  validators.boolean('is_official'),
  validateRequest,
  superadminController.createModule
);
router.put('/marketplace/modules/:id',
  validators.text('name', { min: 3, max: 100 }),
  validators.text('description', { min: 10, max: 5000 }),
  validators.text('version', { min: 1, max: 20 }),
  validators.boolean('is_active'),
  validateRequest,
  superadminController.updateModule
);
router.put('/marketplace/modules/:id/publish', superadminController.publishModule);
router.delete('/marketplace/modules/:id', superadminController.deleteModule);

// Platform configuration management
router.get('/platform-config', PlatformConfigController.getPlatformConfigs);
router.put('/platform-config/:platform',
  validators.text('client_id', { min: 1, max: 500 }),
  validators.text('client_secret', { min: 1, max: 500 }),
  validators.url('redirect_uri'),
  validators.boolean('enabled'),
  validateRequest,
  PlatformConfigController.updatePlatformConfig
);
router.post('/platform-config/:platform/test', PlatformConfigController.testPlatformConnection);

// Hub settings management (signup, email, etc.)
router.get('/settings', PlatformConfigController.getHubSettings);
router.put('/settings',
  validators.boolean('allow_public_signup'),
  validators.boolean('require_email_verification'),
  validators.text('smtp_host', { min: 0, max: 255 }),
  validators.integer('smtp_port', { min: 1, max: 65535 }),
  validators.boolean('smtp_secure'),
  validateRequest,
  PlatformConfigController.updateHubSettings
);

// Kong Gateway management
router.get('/kong/health', kongController.getHealth);
router.get('/kong/status', kongController.getStatus);

// Services
router.get('/kong/services', kongController.getServices);
router.get('/kong/services/:id', kongController.getService);
router.post('/kong/services', kongController.createService);
router.patch('/kong/services/:id', kongController.updateService);
router.delete('/kong/services/:id', kongController.deleteService);

// Routes
router.get('/kong/routes', kongController.getRoutes);
router.get('/kong/routes/:id', kongController.getRoute);
router.get('/kong/services/:serviceId/routes', kongController.getServiceRoutes);
router.post('/kong/services/:serviceId/routes', kongController.createRoute);
router.patch('/kong/routes/:id', kongController.updateRoute);
router.delete('/kong/routes/:id', kongController.deleteRoute);

// Plugins
router.get('/kong/plugins', kongController.getPlugins);
router.get('/kong/plugins/:id', kongController.getPlugin);
router.post('/kong/plugins', kongController.createPlugin);
router.patch('/kong/plugins/:id', kongController.updatePlugin);
router.delete('/kong/plugins/:id', kongController.deletePlugin);

// Consumers
router.get('/kong/consumers', kongController.getConsumers);
router.get('/kong/consumers/:id', kongController.getConsumer);
router.post('/kong/consumers', kongController.createConsumer);
router.delete('/kong/consumers/:id', kongController.deleteConsumer);

// Upstreams
router.get('/kong/upstreams', kongController.getUpstreams);
router.get('/kong/upstreams/:id', kongController.getUpstream);
router.post('/kong/upstreams', kongController.createUpstream);
router.patch('/kong/upstreams/:id', kongController.updateUpstream);
router.delete('/kong/upstreams/:id', kongController.deleteUpstream);

// Targets
router.get('/kong/upstreams/:upstreamId/targets', kongController.getTargets);
router.post('/kong/upstreams/:upstreamId/targets', kongController.createTarget);
router.delete('/kong/upstreams/:upstreamId/targets/:targetId', kongController.deleteTarget);

// Certificates - IMPORTANT: Specific routes must come BEFORE parameterized routes
// Certificate Generation (specific routes first)
router.post('/kong/certificates/generate/self-signed', kongController.generateSelfSigned);
router.post('/kong/certificates/generate/certbot', kongController.generateCertbot);
router.post('/kong/certificates/renew/:domain', kongController.renewCertbot);
router.get('/kong/certificates/certbot/list', kongController.listCertbotCertificates);

// Certificate CRUD (parameterized routes last)
router.get('/kong/certificates', kongController.getCertificates);
router.get('/kong/certificates/:id', kongController.getCertificate);
router.post('/kong/certificates', kongController.createCertificate);
router.delete('/kong/certificates/:id', kongController.deleteCertificate);

// SNIs
router.get('/kong/snis', kongController.getSNIs);
router.post('/kong/snis', kongController.createSNI);
router.delete('/kong/snis/:id', kongController.deleteSNI);

// User management
router.get('/users', userManagementController.listUsers);
router.get('/users/:userId', userManagementController.getUser);
router.post('/users',
  validators.text('email', { min: 5, max: 255 }),
  validators.text('password', { min: 8, max: 255 }),
  validateRequest,
  userManagementController.createUser
);
router.put('/users/:userId',
  validators.text('email', { min: 5, max: 255, required: false }),
  validators.boolean('isActive', { required: false }),
  validateRequest,
  userManagementController.updateUser
);
router.delete('/users/:userId', userManagementController.deleteUser);
router.post('/users/:userId/super-admin-role',
  validators.boolean('grant'),
  validateRequest,
  userManagementController.assignSuperAdminRole
);
router.post('/users/:userId/vendor-role',
  validators.boolean('grant'),
  validateRequest,
  userManagementController.assignVendorRole
);
router.post('/users/:userId/password-reset', userManagementController.generatePasswordReset);

export default router;
