/**
 * Auth Routes - Unified local login with OAuth platform linking
 */
import { Router } from 'express';
import * as authController from '../controllers/authController.js';
import { requireAuth, optionalAuth } from '../middleware/auth.js';
import { validators, validationRules, validateRequest } from '../middleware/validation.js';
import { body } from 'express-validator';

const router = Router();

// Tenant login info (public)
router.get('/tenant/:slug', authController.getTenantLoginInfo);

// Local auth (email/password)
router.post('/register',
  validationRules.register,
  validateRequest,
  authController.register
);
router.post('/login',
  validationRules.login,
  validateRequest,
  authController.login
);
router.post('/admin',
  validationRules.login,
  validateRequest,
  authController.adminLogin
); // Legacy admin login

// Email verification
router.get('/verify-email', authController.verifyEmail);
router.post('/resend-verification',
  validators.email(),
  validateRequest,
  authController.resendVerification
);

// Password management (requires auth)
router.post('/password',
  requireAuth,
  body('newPassword')
    .isLength({ min: 8 })
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/)
    .withMessage('Password must be at least 8 characters with uppercase, lowercase, and number'),
  validateRequest,
  authController.setPassword
);

// OAuth flow
router.get('/oauth/:platform', authController.startOAuth);
router.get('/oauth/:platform/callback', authController.oauthCallback);
// Exchange-code handoff (see authController.oauthCallback /
// redeemOAuthExchangeCode docstrings) -- no session yet at this point, so
// no auth middleware.
router.post('/exchange', authController.redeemOAuthExchangeCode);

// OAuth linking (requires auth)
router.get('/oauth/:platform/link', requireAuth, authController.linkOAuthAccount);
router.get('/oauth/:platform/link-callback', authController.oauthLinkCallback);
router.delete('/oauth/:platform', requireAuth, authController.unlinkOAuthAccount);

// Temp password login (legacy)
router.post('/temp-password', authController.tempPasswordLogin);
router.post('/link-oauth', optionalAuth, authController.linkOAuth);

// Session management
router.post('/refresh', authController.refreshToken);
router.post('/logout', authController.logout);

// Current user info
router.get('/me', optionalAuth, authController.getCurrentUser);

export default router;
