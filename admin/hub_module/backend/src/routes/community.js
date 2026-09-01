/**
 * Community Routes - Authenticated member access
 */
import { Router } from 'express';
import * as communityController from '../controllers/communityController.js';
import * as streamController from '../controllers/streamController.js';
import * as chatController from '../controllers/chatController.js';
import * as activityController from '../controllers/activityController.js';
import * as profileController from '../controllers/profileController.js';
import { requireAuth, requireMember } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';

const router = Router();

// All routes require authentication
router.use(requireAuth);

// User's communities
router.get('/my', communityController.getMyCommunities);

// Create community (any authenticated user)
router.post('/create', communityController.createCommunity);

// Join requests
router.get('/join-requests', communityController.getMyJoinRequests);
router.delete('/join-requests/:requestId', communityController.cancelJoinRequest);

// Server link requests (user's own)
router.get('/server-link-requests', communityController.getMyServerLinkRequests);
router.delete('/server-link-requests/:requestId', communityController.cancelServerLinkRequest);

// Join community (public communities only, no membership required)
router.post('/:id/join', communityController.joinCommunity);

// Server linking (user adds their platform server to community)
router.post('/:id/servers',
  validators.text('platform', { min: 2, max: 50 }),
  validators.text('server_id', { min: 1, max: 255 }),
  validators.text('server_name', { min: 1, max: 255 }),
  validateRequest,
  communityController.addServerToCommunity
);
router.get('/:id/servers', requireMember, communityController.getCommunityServers);

// Community detail (requires membership)
router.get('/:id/dashboard', requireMember, communityController.getCommunityDashboard);
router.get('/:id/leaderboard', requireMember, communityController.getLeaderboard);
router.get('/:id/activity', requireMember, communityController.getActivityFeed);
router.get('/:id/events', requireMember, communityController.getEvents);
router.get('/:id/memories', requireMember, communityController.getMemories);
router.get('/:id/modules', requireMember, communityController.getInstalledModules);
router.get('/:id/members', requireMember, communityController.getCommunityMembers);

// Activity leaderboards (requires membership)
router.get('/:id/leaderboard/watch-time', requireMember, activityController.getWatchTimeLeaderboard);
router.get('/:id/leaderboard/messages', requireMember, activityController.getMessageLeaderboard);
router.get('/:id/activity/my-stats', requireMember, activityController.getMyActivityStats);

// Chat routes
router.get('/:id/chat/history', requireMember, chatController.getChatHistory);
router.get('/:id/chat/channels', requireMember, chatController.getChatChannels);

// Live streams
router.get('/:communityId/streams', requireMember, streamController.getLiveStreams);
router.get('/:communityId/streams/featured', requireMember, streamController.getFeaturedStreams);
router.get('/:communityId/streams/:entityId', requireMember, streamController.getStreamDetails);

// Profile management
router.put('/:id/profile',
  requireMember,
  validators.text('display_name', { min: 2, max: 255 }),
  validators.text('bio', { min: 0, max: 1000 }),
  validators.url('avatar_url'),
  validateRequest,
  communityController.updateProfile
);
router.post('/:id/leave', requireMember, communityController.leaveCommunity);

// Member profiles (requires membership)
router.get('/:id/members/:userId/profile', requireMember, profileController.getMemberProfile);

export default router;
