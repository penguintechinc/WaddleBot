/**
 * Interaction Routes — Hub channels, forums, and internal relay
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin, requireChannelCreation, requireScope } from '../middleware/auth.js';
import * as ctrl from '../controllers/interactionController.js';

const router = Router({ mergeParams: true });

// ── Admin Routes (community admin required) ────────────────────────────

router.get(
  '/:communityId/interaction/channels',
  requireAuth, requireCommunityAdmin,
  ctrl.getHubChannels
);
router.post(
  '/:communityId/interaction/channels',
  requireAuth, requireCommunityAdmin,
  ctrl.createHubChannel
);
router.put(
  '/:communityId/interaction/channels/:id',
  requireAuth, requireCommunityAdmin,
  ctrl.updateHubChannel
);
router.delete(
  '/:communityId/interaction/channels/:id',
  requireAuth, requireCommunityAdmin,
  ctrl.deleteHubChannel
);
router.put(
  '/:communityId/interaction/forum/posts/:id',
  requireAuth, requireCommunityAdmin,
  ctrl.moderateForumPost
);
router.delete(
  '/:communityId/interaction/forum/replies/:id',
  requireAuth, requireCommunityAdmin,
  ctrl.deleteForumReply
);

// Community roles CRUD
router.get('/:communityId/interaction/roles', requireAuth, requireCommunityAdmin, ctrl.getCommunityRoles);
router.post('/:communityId/interaction/roles', requireAuth, requireCommunityAdmin, requireScope('community:manage_roles'), ctrl.createCommunityRole);
router.put('/:communityId/interaction/roles/:roleId', requireAuth, requireCommunityAdmin, requireScope('community:manage_roles'), ctrl.updateCommunityRole);
router.delete('/:communityId/interaction/roles/:roleId', requireAuth, requireCommunityAdmin, requireScope('community:manage_roles'), ctrl.deleteCommunityRole);

// Channel permission overrides
router.get('/:communityId/interaction/channels/:id/permissions', requireAuth, requireCommunityAdmin, ctrl.getChannelPermissionOverrides);
router.put('/:communityId/interaction/channels/:id/permissions', requireAuth, requireCommunityAdmin, requireScope('community:manage_channels'), ctrl.updateChannelPermissionOverrides);

export default router;

// ── Community Member Routes (auth required) ────────────────────────────

export const communityInteractionRouter = Router({ mergeParams: true });

communityInteractionRouter.get(
  '/:id/interact/channels',
  requireAuth,
  ctrl.getHubChannels
);
communityInteractionRouter.post(
  '/:id/interact/channels',
  requireAuth,
  requireChannelCreation,
  ctrl.createHubChannel
);
communityInteractionRouter.get(
  '/:id/interact/forum/:channelId/posts',
  requireAuth,
  ctrl.getForumPosts
);
communityInteractionRouter.get(
  '/:id/interact/forum/:channelId/posts/:postId',
  requireAuth,
  ctrl.getForumPost
);
communityInteractionRouter.post(
  '/:id/interact/forum/:channelId/posts',
  requireAuth,
  ctrl.createForumPost
);
communityInteractionRouter.post(
  '/:id/interact/forum/posts/:postId/replies',
  requireAuth,
  ctrl.createForumReply
);

// ── Internal Relay (service-to-service) ────────────────────────────────

export const internalRelayRouter = Router();

internalRelayRouter.post('/relay/incoming', ctrl.internalRelayIncoming);
