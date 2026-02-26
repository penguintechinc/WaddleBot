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
import callsRoutes, { memberVoiceRouter } from './calls.js';
import pollsRoutes from './polls.js';
import formsRoutes from './forms.js';
import calendarRoutes from './calendar.js';
import calendarAdminRoutes from './calendarAdmin.js';
import supportRoutes from './support.js';
import inventoryRoutes from './inventory.js';
import rconRoutes from './rcon.js';
import tokenRoutes from './tokens.js';
import passkeyRoutes from './passkeys.js';
import joinRequestRoutes from './joinRequests.js';
import interactionAdminRoutes, { communityInteractionRouter, internalRelayRouter } from './interaction.js';
import tenantRoutes from './tenant.js';
import analyticsRoutes from './analytics.js';

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

// Calendar routes (user-facing, auth required)
router.use('/calendar', calendarRoutes);

// Community admin routes (admin role required)
router.use('/admin', adminRoutes);

// Calendar admin routes (community admin required)
router.use('/admin', calendarAdminRoutes);

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

// Support ticket routes (admin + member)
router.use('/admin', supportRoutes);

// Inventory (Quartermaster) routes (admin + member)
router.use('/admin', inventoryRoutes);

// Server Manager (RCON/Voice) routes (admin + member)
router.use('/admin', rconRoutes);

// PAT routes (user-scoped — mount at root, not /admin)
router.use('/', tokenRoutes);
// CAT routes (community-admin-scoped)
router.use('/admin', tokenRoutes);

// Passkey (WebAuthn) routes — auth login + user credential management
router.use('/', passkeyRoutes);

// Community join request routes (member + admin)
router.use('/', joinRequestRoutes);
router.use('/admin', joinRequestRoutes);

// Platform admin routes (platform-admin role required)
router.use('/platform', platformRoutes);

// Analytics routes (self-stats + platform analytics)
router.use('/analytics', analyticsRoutes);

// Super admin routes (super_admin role required)
router.use('/superadmin', superadminRoutes);

// Tenant admin routes (tenant admin role required)
router.use('/tenant', tenantRoutes);

// Interaction routes (hub channels, forums — admin + member)
router.use('/admin', interactionAdminRoutes);
router.use('/community', communityInteractionRouter);

// Member voice routes (interact/voice)
router.use('/community', memberVoiceRouter);

// Internal routes (service-to-service, API key auth)
router.use('/internal', internalRoutes);
router.use('/internal', internalRelayRouter);

export default router;
