/**
 * Community Calls Routes - WebRTC call room management
 */
import { Router } from 'express';
import * as callsController from '../controllers/callsController.js';
import { requireAuth, requireCommunityAdmin } from '../middleware/auth.js';
import { validators, validateRequest } from '../middleware/validation.js';

const router = Router({ mergeParams: true });

// All routes require authentication and community admin role
router.use(requireAuth);

/**
 * Call Rooms
 */

// Get all call rooms for a community
router.get(
  '/:communityId/calls/rooms',
  requireCommunityAdmin,
  callsController.getCallRooms
);

// Get a specific call room
router.get(
  '/:communityId/calls/rooms/:roomName',
  requireCommunityAdmin,
  callsController.getCallRoom
);

// Create a new call room
router.post(
  '/:communityId/calls/rooms',
  requireCommunityAdmin,
  validators.text('room_name', { min: 1, max: 100 }),
  validators.integer('max_participants', { min: 2, max: 1000, optional: true }),
  validateRequest,
  callsController.createCallRoom
);

// Delete a call room
router.delete(
  '/:communityId/calls/rooms/:roomName',
  requireCommunityAdmin,
  callsController.deleteCallRoom
);

/**
 * Room Controls
 */

// Lock a room
router.post(
  '/:communityId/calls/rooms/:roomName/lock',
  requireCommunityAdmin,
  callsController.lockCallRoom
);

// Unlock a room
router.post(
  '/:communityId/calls/rooms/:roomName/unlock',
  requireCommunityAdmin,
  callsController.unlockCallRoom
);

/**
 * Participant Management
 */

// Get participants in a room
router.get(
  '/:communityId/calls/rooms/:roomName/participants',
  requireCommunityAdmin,
  callsController.getCallParticipants
);

// Kick a participant
router.post(
  '/:communityId/calls/rooms/:roomName/kick',
  requireCommunityAdmin,
  validators.text('identity', { min: 1, max: 255 }),
  validateRequest,
  callsController.kickCallParticipant
);

// Mute all participants
router.post(
  '/:communityId/calls/rooms/:roomName/mute-all',
  requireCommunityAdmin,
  callsController.muteAllCallParticipants
);

/**
 * Raised Hands
 */

// Get raised hands queue
router.get(
  '/:communityId/calls/rooms/:roomName/raised-hands',
  requireCommunityAdmin,
  callsController.getRaisedHands
);

// Acknowledge a raised hand
router.post(
  '/:communityId/calls/rooms/:roomName/acknowledge-hand',
  requireCommunityAdmin,
  validators.text('user_id', { min: 1, max: 255 }),
  validateRequest,
  callsController.acknowledgeHand
);

/**
 * Member-facing voice routes (auth required, no admin)
 * These are mounted under /community by the interaction routes
 */
export const memberVoiceRouter = Router({ mergeParams: true });
memberVoiceRouter.use(requireAuth);

memberVoiceRouter.get(
  '/:id/interact/voice/rooms',
  callsController.getCallRooms
);
memberVoiceRouter.post(
  '/:id/interact/voice/rooms',
  callsController.createCallRoom
);
memberVoiceRouter.post(
  '/:id/interact/voice/rooms/:roomName/join',
  callsController.joinVoiceRoom
);
memberVoiceRouter.post(
  '/:id/interact/voice/rooms/:roomName/leave',
  callsController.leaveVoiceRoom
);

export default router;
