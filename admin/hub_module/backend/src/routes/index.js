/**
 * Route Aggregator
 * Combines all API routes under /api/v1
 */
import { Router } from 'express';
import publicRoutes from './public.js';
import authRoutes from './auth.js';
import userRoutes from './user.js';
import communityRoutes from './community.js';
import adminRoutes from './admin.js';
import marketplaceRoutes from './marketplace.js';
import platformRoutes from './platform.js';
import superadminRoutes from './superadmin.js';
import internalRoutes from './internal.js';
import cookieConsentRoutes from './cookieConsent.js';
import streamingRoutes from './streaming.js';
import callsRoutes from './calls.js';
import pollsRoutes from './polls.js';
import formsRoutes from './forms.js';

const router = Router();

// Signup settings (top-level alias for /public/signup-settings)
router.get('/signup-settings', (req, res, next) => {
  req.url = '/signup-settings';
  publicRoutes(req, res, next);
});

// Public routes (no auth required)
router.use('/public', publicRoutes);

// Cookie consent routes
router.use('/cookie', cookieConsentRoutes);

// Auth routes
router.use('/auth', authRoutes);

// User routes (auth required - identity linking, profile)
router.use('/user', userRoutes);

// Community member routes (auth required)
router.use('/community', communityRoutes);
router.use('/communities', communityRoutes); // Alias for plural form

// Community admin routes (admin role required)
router.use('/admin', adminRoutes);

// Streaming management routes (admin role required)
router.use('/admin', streamingRoutes);

// Community calls routes (admin role required)
router.use('/admin', callsRoutes);

// Polls management routes (admin role required)
router.use('/admin', pollsRoutes);

// Forms management routes (admin role required)
router.use('/admin', formsRoutes);

// Marketplace routes (admin role required)
router.use('/admin', marketplaceRoutes);

// Platform admin routes (platform-admin role required)
router.use('/platform', platformRoutes);

// Super admin routes (super_admin role required)
router.use('/superadmin', superadminRoutes);

// Internal routes (service-to-service, API key auth)
router.use('/internal', internalRoutes);

export default router;
