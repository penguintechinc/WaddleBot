/**
 * Router Integration Controller — internal endpoints for the router module
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';
import * as vendorExecutionService from '../services/vendorExecutionService.js';

export async function getCommunityCommands(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId);

    const { rows } = await query(
      `SELECT command, module_name, module_url, description, usage, category,
              permission_level, is_enabled, cooldown_seconds
       FROM commands
       WHERE community_id=$1
         AND module_name LIKE 'marketplace:%'
         AND is_enabled=true`,
      [communityId]
    );

    return res.json({ success: true, commands: rows });
  } catch (err) {
    next(err);
  }
}

export async function executeModuleCommand(req, res, next) {
  try {
    const moduleId = parseInt(req.params.moduleId);
    const payload = req.body;

    vendorExecutionService.incrementRequestCount(moduleId);

    const result = await vendorExecutionService.executeCommand(moduleId, payload);

    return res.json(result);
  } catch (err) {
    next(err);
  }
}
