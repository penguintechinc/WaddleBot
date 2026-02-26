/**
 * Passkey Routes
 */
import { Router } from 'express';
import { requireAuth } from '../middleware/auth.js';
import * as passkeyController from '../controllers/passkeyController.js';

const router = Router({ mergeParams: true });

// Auth routes (no auth required — login flow)
router.post('/auth/passkey/login/start', passkeyController.startLogin);
router.post('/auth/passkey/login/finish', passkeyController.finishLogin);

// User routes (auth required — manage credentials)
router.post('/user/passkey/register/start', requireAuth, passkeyController.startRegistration);
router.post('/user/passkey/register/finish', requireAuth, passkeyController.finishRegistration);
router.get('/user/passkey/credentials', requireAuth, passkeyController.listCredentials);
router.delete('/user/passkey/credentials/:id', requireAuth, passkeyController.removeCredential);

export default router;
