/**
 * User Routes - Identity linking and user management
 */
import { Router } from 'express';
import multer from 'multer';
import * as identityController from '../controllers/identityController.js';
import * as profileController from '../controllers/profileController.js';
import PlatformConfigController from '../controllers/platformConfigController.js';
import { requireAuth } from '../middleware/auth.js';
import * as dataPrivacyController from '../controllers/dataPrivacyController.js';
import { validators, validateRequest } from '../middleware/validation.js';

const router = Router();

// Configure multer for avatar uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
});

// All user routes require authentication
router.use(requireAuth);

// Profile routes
router.get('/profile', profileController.getMyProfile);
router.put('/profile',
  validators.text('display_name', { min: 2, max: 255 }),
  validators.text('bio', { min: 0, max: 1000 }),
  validators.text('location', { min: 0, max: 255 }),
  validators.url('website'),
  validateRequest,
  profileController.updateMyProfile
);
router.post('/profile/avatar', upload.single('avatar'), profileController.uploadAvatar);
router.delete('/profile/avatar', profileController.deleteAvatar);
router.get('/linked-platforms', profileController.getMyLinkedPlatforms);

// User OAuth credential management (authenticated user, own credentials only)
router.get('/oauth/credentials', PlatformConfigController.getMyCredentials);
router.post('/oauth/credentials', PlatformConfigController.createMyCredential);
router.put('/oauth/credentials/:id', PlatformConfigController.updateMyCredential);
router.delete('/oauth/credentials/:id', PlatformConfigController.deleteMyCredential);
router.post('/oauth/credentials/:id/test', PlatformConfigController.testCredential);

// Identity linking routes
router.get('/identities', identityController.getLinkedIdentities);
router.get('/identities/primary', identityController.getPrimaryIdentity);
router.put('/identities/primary',
  validators.text('platform', { min: 2, max: 50 }),
  validators.text('platform_user_id', { min: 1, max: 255 }),
  validateRequest,
  identityController.setPrimaryIdentity
);
router.post('/identities/link/:platform', identityController.startIdentityLink);
router.get('/identities/link/:platform/callback', identityController.identityLinkCallback);
router.delete('/identities/:platform', identityController.unlinkIdentity);

// GDPR: data deletion (auth already required at top via router.use(requireAuth))
router.get('/me/data', dataPrivacyController.exportUserData);
router.delete('/me/data', dataPrivacyController.requestDataDeletion);

export default router;
