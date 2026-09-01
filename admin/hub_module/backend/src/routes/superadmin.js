/**
 * Super Admin Routes - Global admin features for managing all communities
 */
import { Router } from 'express';
import * as superadminController from '../controllers/superadminController.js';
import * as analyticsController from '../controllers/analyticsController.js';
import PlatformConfigController from '../controllers/platformConfigController.js';
import * as userManagementController from '../controllers/userManagementController.js';
import { requireAuth, requireSuperAdmin } from '../middleware/auth.js';
import { validators, validationRules, validateRequest } from '../middleware/validation.js';

const router = Router();

// All routes require super admin authentication
router.use(requireAuth);
router.use(requireSuperAdmin);

// Dashboard stats
router.get('/dashboard', superadminController.getDashboardStats);

// Analytics
router.get('/analytics', analyticsController.getPlatformOverview);
router.get('/analytics/reputation', analyticsController.getReputationDistribution);
router.get('/analytics/growth', analyticsController.getGrowthTrends);
router.get('/analytics/activity', analyticsController.getActivityBreakdown);

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
router.post('/users/:userId/verify-email',
  validators.boolean('verified'),
  validateRequest,
  userManagementController.setEmailVerification
);
router.post('/users/:userId/password-reset', userManagementController.generatePasswordReset);
router.post('/users/:userId/analytics-consumer-role', userManagementController.assignAnalyticsConsumerRole);
router.get('/users/:userId/deletion-request', userManagementController.getUserDeletionRequest);

// Tenant management
router.get('/tenants', superadminController.listTenants);
router.post('/tenants', superadminController.createTenant);
router.put('/tenants/:id', superadminController.updateTenant);
router.delete('/tenants/:id', superadminController.deleteTenant);

export default router;
