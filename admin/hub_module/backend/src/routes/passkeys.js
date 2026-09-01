/**
 * Passkey Routes
 */
import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import * as passkeyController from '../controllers/passkeyController.js';

const router = Router({ mergeParams: true });

// Auth routes (no auth required — login flow)
router.post('/api/v1/auth/passkey/login/start', passkeyController.startLogin);
router.post('/api/v1/auth/passkey/login/finish', passkeyController.finishLogin);

// User routes (auth required — manage credentials)
router.post('/api/v1/user/passkey/register/start', requireAuth, passkeyController.startRegistration);
router.post('/api/v1/user/passkey/register/finish', requireAuth, passkeyController.finishRegistration);
router.get('/api/v1/user/passkey/credentials', requireAuth, passkeyController.listCredentials);
router.delete('/api/v1/user/passkey/credentials/:id', requireAuth, passkeyController.removeCredential);

export default router;
