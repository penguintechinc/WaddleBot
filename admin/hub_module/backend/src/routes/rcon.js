/**
 * Server Manager (RCON/Voice) Routes
 */
import { Router } from 'express';
import { requireAuth, requireCommunityAdmin, requireMember } from '../middleware/auth.js';
import {
  listServers,
  createServer,
  updateServer,
  deleteServer,
  testConnection,
  executeCommand,
  getServerStatus,
  getPlayerList,
  kickPlayer,
  banPlayer,
  getChannels,
  moveUser,
  sendMessage,
  getCommandLog,
  getAccessPolicy,
  updateAccessPolicy,
  triggerEnforcement,
  getAccessLog,
} from '../controllers/rconController.js';

const router = Router({ mergeParams: true });

// ── Admin Routes ───────────────────────────────────────────────

router.get('/:communityId/rcon/servers', requireAuth, requireCommunityAdmin, listServers);
router.post('/:communityId/rcon/servers', requireAuth, requireCommunityAdmin, createServer);
router.put('/:communityId/rcon/servers/:serverId', requireAuth, requireCommunityAdmin, updateServer);
router.delete('/:communityId/rcon/servers/:serverId', requireAuth, requireCommunityAdmin, deleteServer);

router.post('/:communityId/rcon/servers/:serverId/test', requireAuth, requireCommunityAdmin, testConnection);
router.post('/:communityId/rcon/servers/:serverId/command', requireAuth, requireCommunityAdmin, executeCommand);
router.post('/:communityId/rcon/servers/:serverId/kick', requireAuth, requireCommunityAdmin, kickPlayer);
router.post('/:communityId/rcon/servers/:serverId/ban', requireAuth, requireCommunityAdmin, banPlayer);

router.get('/:communityId/rcon/servers/:serverId/channels', requireAuth, requireCommunityAdmin, getChannels);
router.post('/:communityId/rcon/servers/:serverId/move', requireAuth, requireCommunityAdmin, moveUser);
router.post('/:communityId/rcon/servers/:serverId/message', requireAuth, requireCommunityAdmin, sendMessage);

router.get('/:communityId/rcon/log', requireAuth, requireCommunityAdmin, getCommandLog);

router.get('/:communityId/rcon/servers/:serverId/policy', requireAuth, requireCommunityAdmin, getAccessPolicy);
router.put('/:communityId/rcon/servers/:serverId/policy', requireAuth, requireCommunityAdmin, updateAccessPolicy);
router.post('/:communityId/rcon/servers/:serverId/enforce', requireAuth, requireCommunityAdmin, triggerEnforcement);
router.get('/:communityId/rcon/servers/:serverId/access-log', requireAuth, requireCommunityAdmin, getAccessLog);

// ── Member Routes ──────────────────────────────────────────────
// requireMember confirms the caller actually belongs to :communityId --
// requireAuth alone only confirms they are logged in as *someone*, which
// let any authenticated user query any other community's server status
// (OWASP A01, cross-community BOLA -- see rconController.js's
// verifyServerBelongsToCommunity for the matching :serverId ownership fix).

router.get('/:communityId/rcon/info', requireAuth, requireMember, listServers);
router.get('/:communityId/rcon/info/:serverId/status', requireAuth, requireMember, getServerStatus);
router.get('/:communityId/rcon/info/:serverId/players', requireAuth, requireMember, getPlayerList);

export default router;
