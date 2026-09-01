/**
 * Admin Routes - Community admin access
 */
import { Router } from 'express';
import multer from 'multer';
import * as adminController from '../controllers/adminController.js';
import * as activityController from '../controllers/activityController.js';
import * as communityController from '../controllers/communityController.js';
import * as communityProfileController from '../controllers/communityProfileController.js';
import * as overlayController from '../controllers/overlayController.js';
import * as loyaltyController from '../controllers/loyaltyController.js';
import * as announcementController from '../controllers/announcementController.js';
import * as aiChatterController from '../controllers/aiChatterController.js';
import PlatformConfigController from '../controllers/platformConfigController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';
import { isAllowedProxyPath } from '../utils/proxyAllowlist.js';
import workflowRoutes from './workflow.js';

const router = Router();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 5 * 1024 * 1024 }, // 5MB
});

router.use(requireAuth);

// Members management
router.get('/:communityId/members', requireCommunityAdmin, adminController.getMembers);
router.put('/:communityId/members/:userId/role', requireCommunityAdmin, adminController.updateMemberRole);
router.put('/:communityId/members/:userId/reputation', requireCommunityAdmin, adminController.adjustReputation);
router.delete('/:communityId/members/:userId', requireCommunityAdmin, adminController.removeMember);
router.post('/:communityId/members/:userId/temp-password', requireCommunityAdmin, adminController.generateTempPassword);

// Modules management
router.get('/:communityId/modules', requireCommunityAdmin, adminController.getModules);
router.put('/:communityId/modules/:moduleId/config', requireCommunityAdmin, adminController.updateModuleConfig);

// Browser sources
router.get('/:communityId/browser-sources', requireCommunityAdmin, adminController.getBrowserSources);
router.post('/:communityId/browser-sources/regenerate', requireCommunityAdmin, adminController.regenerateBrowserSources);

// Custom domains
router.get('/:communityId/domains', requireCommunityAdmin, adminController.getDomains);
router.post('/:communityId/domains', requireCommunityAdmin, adminController.addDomain);
router.post('/:communityId/domains/:domainId/verify', requireCommunityAdmin, adminController.verifyDomain);
router.delete('/:communityId/domains/:domainId', requireCommunityAdmin, adminController.removeDomain);

// Linked servers
router.get('/:communityId/servers', requireCommunityAdmin, adminController.getLinkedServers);
router.put('/:communityId/servers/:serverId', requireCommunityAdmin, adminController.updateServer);
router.delete('/:communityId/servers/:serverId', requireCommunityAdmin, adminController.removeServer);

// Community settings
router.get('/:communityId/settings', requireCommunityAdmin, adminController.getCommunitySettings);
router.put('/:communityId/settings', requireCommunityAdmin, adminController.updateCommunitySettings);

// Join requests
router.get('/:communityId/join-requests', requireCommunityAdmin, adminController.getJoinRequests);
router.post('/:communityId/join-requests/:requestId/approve', requireCommunityAdmin, adminController.approveJoinRequest);
router.post('/:communityId/join-requests/:requestId/reject', requireCommunityAdmin, adminController.rejectJoinRequest);

// Server link requests
router.get('/:communityId/server-link-requests', requireCommunityAdmin, adminController.getServerLinkRequests);
router.post('/:communityId/server-link-requests', requireCommunityAdmin, adminController.createServerLinkRequest);
router.post('/:communityId/server-link-requests/:requestId/approve', requireCommunityAdmin, adminController.approveServerLinkRequest);
router.post('/:communityId/server-link-requests/:requestId/reject', requireCommunityAdmin, adminController.rejectServerLinkRequest);

// Commands reference
router.get('/:communityId/commands', requireCommunityAdmin, adminController.getCommands);

// Mirror groups
router.get('/:communityId/mirror-groups', requireCommunityAdmin, adminController.getMirrorGroups);
router.post('/:communityId/mirror-groups',
  requireCommunityAdmin,
  validators.text('name', { min: 3, max: 100 }),
  validators.text('description', { min: 0, max: 500 }),
  validators.boolean('is_active'),
  validateRequest,
  adminController.createMirrorGroup
);
router.get('/:communityId/mirror-groups/:groupId', requireCommunityAdmin, adminController.getMirrorGroup);
router.put('/:communityId/mirror-groups/:groupId',
  requireCommunityAdmin,
  validators.text('name', { min: 3, max: 100 }),
  validators.text('description', { min: 0, max: 500 }),
  validators.boolean('is_active'),
  validateRequest,
  adminController.updateMirrorGroup
);
router.delete('/:communityId/mirror-groups/:groupId', requireCommunityAdmin, adminController.deleteMirrorGroup);

// Mirror group members
router.post('/:communityId/mirror-groups/:groupId/members',
  requireCommunityAdmin,
  validators.integer('server_id', { min: 1 }),
  validators.text('channel_id', { min: 1, max: 255 }),
  validateRequest,
  adminController.addMirrorGroupMember
);
router.put('/:communityId/mirror-groups/:groupId/members/:memberId',
  requireCommunityAdmin,
  validators.boolean('is_active'),
  validateRequest,
  adminController.updateMirrorGroupMember
);
router.delete('/:communityId/mirror-groups/:groupId/members/:memberId', requireCommunityAdmin, adminController.removeMirrorGroupMember);

// Leaderboard configuration
router.get('/:communityId/leaderboard-config', requireCommunityAdmin, activityController.getLeaderboardConfig);
router.put('/:communityId/leaderboard-config',
  requireCommunityAdmin,
  validators.boolean('show_watch_time'),
  validators.boolean('show_messages'),
  validators.boolean('show_reputation'),
  validators.integer('default_limit', { min: 1, max: 100 }),
  validateRequest,
  activityController.updateLeaderboardConfig
);

// Community profile management
router.put('/:communityId/profile',
  requireCommunityAdmin,
  validators.text('display_name', { min: 3, max: 255 }),
  validators.text('tagline', { min: 0, max: 255 }),
  validators.text('description', { min: 0, max: 5000 }),
  validators.hexColor('primary_color'),
  validators.hexColor('secondary_color'),
  validateRequest,
  communityProfileController.updateCommunityProfile
);
router.post('/:communityId/logo', requireCommunityAdmin, upload.single('logo'), communityProfileController.uploadCommunityLogo);
router.delete('/:communityId/logo', requireCommunityAdmin, communityProfileController.deleteCommunityLogo);
router.post('/:communityId/banner', requireCommunityAdmin, upload.single('banner'), communityProfileController.uploadCommunityBanner);
router.delete('/:communityId/banner', requireCommunityAdmin, communityProfileController.deleteCommunityBanner);

// Reputation configuration (FICO-style scoring system)
router.get('/:communityId/reputation/config', requireCommunityAdmin, adminController.getReputationConfig);
router.put('/:communityId/reputation/config',
  requireCommunityAdmin,
  validators.integer('base_score', { min: 0, max: 1000 }),
  validators.integer('min_score', { min: 0 }),
  validators.integer('max_score', { min: 0 }),
  validators.boolean('enabled'),
  validateRequest,
  adminController.updateReputationConfig
);
router.get('/:communityId/reputation/at-risk', requireCommunityAdmin, adminController.getAtRiskUsers);
router.get('/:communityId/reputation/leaderboard', requireCommunityAdmin, adminController.getReputationLeaderboard);

// AI Insights
router.get('/:communityId/ai-insights', requireCommunityAdmin, adminController.getAIInsights);
router.get('/:communityId/ai-insights/:insightId', requireCommunityAdmin, adminController.getAIInsight);

// AI Researcher Config
router.get('/:communityId/ai-researcher/config', requireCommunityAdmin, adminController.getAIResearcherConfig);
router.put('/:communityId/ai-researcher/config',
  requireCommunityAdmin,
  validators.boolean('enabled'),
  validators.integer('analysis_interval_hours', { min: 1, max: 168 }),
  validators.arrayOfStrings('focus_areas'),
  validateRequest,
  adminController.updateAIResearcherConfig
);
router.get('/:communityId/ai-researcher/available-models', requireCommunityAdmin, adminController.getAvailableAIModels);

// Bot Detection
router.get('/:communityId/bot-detection', requireCommunityAdmin, adminController.getBotDetectionResults);
router.post('/:communityId/bot-detection/:resultId/review',
  requireCommunityAdmin,
  validators.boolean('is_bot'),
  validators.text('notes', { min: 0, max: 1000 }),
  validateRequest,
  adminController.reviewBotDetection
);

// Context Visualization
router.get('/:communityId/ai-context', requireCommunityAdmin, adminController.getAIContext);

// Overlay management
router.get('/:communityId/overlay', requireCommunityAdmin, overlayController.getOverlay);
router.put('/:communityId/overlay',
  requireCommunityAdmin,
  validators.text('title', { min: 0, max: 255 }),
  validators.text('subtitle', { min: 0, max: 255 }),
  validators.hexColor('background_color'),
  validators.hexColor('text_color'),
  validators.integer('refresh_interval', { min: 1000, max: 60000 }),
  validateRequest,
  overlayController.updateOverlay
);
router.post('/:communityId/overlay/rotate', requireCommunityAdmin, overlayController.rotateKey);
router.get('/:communityId/overlay/stats', requireCommunityAdmin, overlayController.getOverlayStats);

// Loyalty module - Currency configuration
router.get('/:communityId/loyalty/config', requireCommunityAdmin, loyaltyController.getConfig);
router.put('/:communityId/loyalty/config',
  requireCommunityAdmin,
  validators.text('currency_name', { min: 1, max: 50 }),
  validators.text('currency_plural', { min: 1, max: 50 }),
  validators.positiveInteger('earn_rate_per_minute'),
  validators.positiveInteger('bonus_multiplier'),
  validators.boolean('enabled'),
  validateRequest,
  loyaltyController.updateConfig
);

// Loyalty module - Currency management
router.get('/:communityId/loyalty/leaderboard', requireCommunityAdmin, loyaltyController.getLeaderboard);
router.put('/:communityId/loyalty/user/:userId/balance',
  requireCommunityAdmin,
  validators.integer('amount'),
  validators.text('reason', { min: 0, max: 255 }),
  validateRequest,
  loyaltyController.adjustUserBalance
);
router.post('/:communityId/loyalty/wipe', requireCommunityAdmin, loyaltyController.wipeAllCurrency);
router.get('/:communityId/loyalty/stats', requireCommunityAdmin, loyaltyController.getStats);

// Loyalty module - Giveaways
router.get('/:communityId/loyalty/giveaways', requireCommunityAdmin, loyaltyController.getGiveaways);
router.post('/:communityId/loyalty/giveaways',
  requireCommunityAdmin,
  validators.text('title', { min: 3, max: 255 }),
  validators.text('description', { min: 0, max: 1000 }),
  validators.positiveInteger('entry_cost'),
  validators.positiveInteger('max_entries_per_user'),
  ...validators.dateRange(),
  validateRequest,
  loyaltyController.createGiveaway
);
router.get('/:communityId/loyalty/giveaways/:giveawayId/entries', requireCommunityAdmin, loyaltyController.getGiveawayEntries);
router.post('/:communityId/loyalty/giveaways/:giveawayId/draw', requireCommunityAdmin, loyaltyController.drawGiveawayWinner);
router.put('/:communityId/loyalty/giveaways/:giveawayId/end', requireCommunityAdmin, loyaltyController.endGiveaway);

// Loyalty module - Games
router.get('/:communityId/loyalty/games/config', requireCommunityAdmin, loyaltyController.getGamesConfig);
router.put('/:communityId/loyalty/games/config',
  requireCommunityAdmin,
  validators.boolean('slots_enabled'),
  validators.boolean('roulette_enabled'),
  validators.boolean('coinflip_enabled'),
  validators.positiveInteger('min_bet'),
  validators.positiveInteger('max_bet'),
  validateRequest,
  loyaltyController.updateGamesConfig
);
router.get('/:communityId/loyalty/games/stats', requireCommunityAdmin, loyaltyController.getGamesStats);
router.get('/:communityId/loyalty/games/recent', requireCommunityAdmin, loyaltyController.getRecentGames);

// Loyalty module - Gear shop
router.get('/:communityId/loyalty/gear/categories', requireCommunityAdmin, loyaltyController.getGearCategories);
router.get('/:communityId/loyalty/gear/items', requireCommunityAdmin, loyaltyController.getGearItems);
router.post('/:communityId/loyalty/gear/items',
  requireCommunityAdmin,
  validators.text('name', { min: 3, max: 255 }),
  validators.text('description', { min: 0, max: 1000 }),
  validators.positiveInteger('price'),
  validators.positiveInteger('stock'),
  validators.integer('category_id', { min: 1 }),
  validators.boolean('is_active'),
  validateRequest,
  loyaltyController.createGearItem
);
router.put('/:communityId/loyalty/gear/items/:itemId',
  requireCommunityAdmin,
  validators.text('name', { min: 3, max: 255 }),
  validators.text('description', { min: 0, max: 1000 }),
  validators.positiveInteger('price'),
  validators.positiveInteger('stock'),
  validators.boolean('is_active'),
  validateRequest,
  loyaltyController.updateGearItem
);
router.delete('/:communityId/loyalty/gear/items/:itemId', requireCommunityAdmin, loyaltyController.deleteGearItem);
router.get('/:communityId/loyalty/gear/stats', requireCommunityAdmin, loyaltyController.getGearStats);

// Announcements (admin & moderator access)
router.get('/:communityId/announcements', requireCommunityAdmin, announcementController.getAnnouncements);
router.get('/:communityId/announcements/:announcementId', requireCommunityAdmin, announcementController.getAnnouncement);
router.post('/:communityId/announcements', requireCommunityAdmin, announcementController.createAnnouncement);
router.put('/:communityId/announcements/:announcementId', requireCommunityAdmin, announcementController.updateAnnouncement);
router.delete('/:communityId/announcements/:announcementId', requireCommunityAdmin, announcementController.deleteAnnouncement);

// Announcement actions
router.post('/:communityId/announcements/:announcementId/publish', requireCommunityAdmin, announcementController.publishAnnouncement);
router.put('/:communityId/announcements/:announcementId/pin', requireCommunityAdmin, announcementController.pinAnnouncement);
router.put('/:communityId/announcements/:announcementId/unpin', requireCommunityAdmin, announcementController.unpinAnnouncement);
router.post('/:communityId/announcements/:announcementId/archive', requireCommunityAdmin, announcementController.archiveAnnouncement);

// Broadcasting
router.post('/:communityId/announcements/:announcementId/broadcast', requireCommunityAdmin, announcementController.broadcastAnnouncement);
router.get('/:communityId/announcements/:announcementId/broadcast-status', requireCommunityAdmin, announcementController.getBroadcastStatus);

// Bot Score (Community health grade A-F)
router.get('/:communityId/bot-score', requireCommunityAdmin, adminController.getBotScore);
router.get('/:communityId/suspected-bots', requireCommunityAdmin, adminController.getSuspectedBots);
router.put('/:communityId/suspected-bots/:botId/review',
  requireCommunityAdmin,
  validators.boolean('is_bot'),
  validators.text('review_notes', { min: 0, max: 1000 }),
  validateRequest,
  adminController.reviewSuspectedBot
);

// Analytics proxy routes
router.get('/:communityId/analytics/*', requireCommunityAdmin, async (req, res) => {
  try {
    const analyticsPath = req.params[0];
    if (!isAllowedProxyPath('analytics', 'GET', analyticsPath)) {
      return res.status(403).json({ error: 'Requested analytics path is not permitted' });
    }
    const httpClient = (await import('axios')).default;
    const response = await httpClient.get(
      `http://analytics-core:8040/api/v1/analytics/${req.params.communityId}/${analyticsPath}`,
      {
        params: req.query,
        headers: {
          'X-API-Key': req.headers['x-api-key'],
          'X-Community-ID': req.params.communityId,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
      return res.json({ success: true, unavailable: true, message: 'Analytics service not available' });
    }
    console.error('Analytics proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.response?.data?.error || 'Failed to fetch analytics',
    });
  }
});

// Helper: check if error is a connection failure (service not deployed)
function isServiceUnavailable(error) {
  return error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND';
}

// Security proxy routes
router.get('/:communityId/security/*', requireCommunityAdmin, async (req, res) => {
  try {
    const securityPath = req.params[0];
    if (!isAllowedProxyPath('security', 'GET', securityPath)) {
      return res.status(403).json({ error: 'Requested security path is not permitted' });
    }
    const httpClient = (await import('axios')).default;
    const response = await httpClient.get(
      `http://security-core:8041/api/v1/security/${req.params.communityId}/${securityPath}`,
      {
        params: req.query,
        headers: {
          'X-API-Key': req.headers['x-api-key'],
          'X-Community-ID': req.params.communityId,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    if (isServiceUnavailable(error)) {
      return res.json({ success: true, unavailable: true, message: 'Security service not available' });
    }
    console.error('Security proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.response?.data?.error || 'Failed to fetch security data',
    });
  }
});

router.put('/:communityId/security/*', requireCommunityAdmin, async (req, res) => {
  try {
    const securityPath = req.params[0];
    if (!isAllowedProxyPath('security', 'PUT', securityPath)) {
      return res.status(403).json({ error: 'Requested security path is not permitted' });
    }
    const httpClient = (await import('axios')).default;
    const response = await httpClient.put(
      `http://security-core:8041/api/v1/security/${req.params.communityId}/${securityPath}`,
      req.body,
      {
        params: req.query,
        headers: {
          'X-API-Key': req.headers['x-api-key'],
          'X-Community-ID': req.params.communityId,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    if (isServiceUnavailable(error)) {
      return res.json({ success: true, unavailable: true, message: 'Security service not available' });
    }
    console.error('Security proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.response?.data?.error || 'Failed to update security settings',
    });
  }
});

router.post('/:communityId/security/*', requireCommunityAdmin, async (req, res) => {
  try {
    const securityPath = req.params[0];
    if (!isAllowedProxyPath('security', 'POST', securityPath)) {
      return res.status(403).json({ error: 'Requested security path is not permitted' });
    }
    const httpClient = (await import('axios')).default;
    const response = await httpClient.post(
      `http://security-core:8041/api/v1/security/${req.params.communityId}/${securityPath}`,
      req.body,
      {
        params: req.query,
        headers: {
          'X-API-Key': req.headers['x-api-key'],
          'X-Community-ID': req.params.communityId,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    if (isServiceUnavailable(error)) {
      return res.json({ success: true, unavailable: true, message: 'Security service not available' });
    }
    console.error('Security proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.response?.data?.error || 'Failed to process security action',
    });
  }
});

router.delete('/:communityId/security/*', requireCommunityAdmin, async (req, res) => {
  try {
    const securityPath = req.params[0];
    if (!isAllowedProxyPath('security', 'DELETE', securityPath)) {
      return res.status(403).json({ error: 'Requested security path is not permitted' });
    }
    const httpClient = (await import('axios')).default;
    const response = await httpClient.delete(
      `http://security-core:8041/api/v1/security/${req.params.communityId}/${securityPath}`,
      {
        params: req.query,
        headers: {
          'X-API-Key': req.headers['x-api-key'],
          'X-Community-ID': req.params.communityId,
        },
      }
    );
    res.json(response.data);
  } catch (error) {
    if (isServiceUnavailable(error)) {
      return res.json({ success: true, unavailable: true, message: 'Security service not available' });
    }
    console.error('Security proxy error:', error.message);
    res.status(error.response?.status || 500).json({
      error: error.response?.data?.error || 'Failed to delete security item',
    });
  }
});

// Connected platforms (aggregates from community_servers)
router.get('/:communityId/connected-platforms', requireCommunityAdmin, adminController.getConnectedPlatforms);

// Community OAuth credential management (community admin only)
router.get('/:communityId/oauth/credentials', requireCommunityAdmin, PlatformConfigController.getCommunityCredentials);
router.post('/:communityId/oauth/credentials', requireCommunityAdmin, PlatformConfigController.createCommunityCredential);
router.put('/:communityId/oauth/credentials/:id', requireCommunityAdmin, PlatformConfigController.updateCommunityCredential);
router.delete('/:communityId/oauth/credentials/:id', requireCommunityAdmin, PlatformConfigController.deleteCommunityCredential);
router.post('/:communityId/oauth/credentials/:id/test', requireCommunityAdmin, PlatformConfigController.testCredential);

// Shoutout management
router.get('/:communityId/shoutout/config', requireCommunityAdmin, adminController.getShoutoutConfig);
router.put('/:communityId/shoutout/config', requireCommunityAdmin, adminController.updateShoutoutConfig);
router.get('/:communityId/shoutout/creators', requireCommunityAdmin, adminController.getShoutoutCreators);
router.post('/:communityId/shoutout/creators', requireCommunityAdmin, adminController.addShoutoutCreator);
router.delete('/:communityId/shoutout/creators/:creatorId', requireCommunityAdmin, adminController.removeShoutoutCreator);
router.get('/:communityId/shoutout/history', requireCommunityAdmin, adminController.getShoutoutHistory);

// Translation configuration routes
router.get('/:communityId/translation/config', requireCommunityAdmin, adminController.getTranslationConfig);
router.put('/:communityId/translation/config', requireCommunityAdmin, adminController.updateTranslationConfig);

// Workflow routes
router.use('/:communityId/workflows', workflowRoutes);

// AI Chatter configuration
router.get('/:communityId/ai-chatter/config', requireCommunityAdmin, aiChatterController.getChatterConfig);
router.put('/:communityId/ai-chatter/config', requireCommunityAdmin, aiChatterController.updateChatterConfig);

export default router;
