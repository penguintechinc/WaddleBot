/**
 * Command Registration Service
 * Registers/unregisters marketplace module commands in the commands table
 * and broadcasts reload events via Redis pub/sub.
 */
import { createClient } from 'redis';
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';

let redisClient = null;

async function getRedisClient() {
  if (!redisClient) {
    redisClient = createClient({
      url: process.env.REDIS_URL || 'redis://redis:6379',
    });
    redisClient.on('error', (err) =>
      logger.error('Redis client error', { error: err.message })
    );
    await redisClient.connect();
  }
  return redisClient;
}

/**
 * Registers all trigger commands for a marketplace module into the commands table.
 * @param {number} communityId
 * @param {object} module - { id, trigger_commands, name, description, category }
 */
export async function registerModuleCommands(communityId, module) {
  if (!module.trigger_commands || module.trigger_commands.length === 0) {
    logger.warn('registerModuleCommands: no trigger_commands to register', {
      communityId,
      moduleId: module.id,
    });
    return;
  }

  const moduleName = 'marketplace:' + module.id;
  const moduleUrl = 'http://marketplace:8100/api/v1/internal/execute/' + module.id;
  const category = module.category || 'marketplace';

  for (const command of module.trigger_commands) {
    const description = module.description || command;
    await query(
      `INSERT INTO commands
        (command, module_name, module_url, description, usage, category, permission_level, is_enabled, cooldown_seconds, community_id)
       VALUES ($1, $2, $3, $4, $5, $6, 'everyone', true, 3, $7)
       ON CONFLICT (command, community_id) DO UPDATE
         SET module_name = EXCLUDED.module_name,
             module_url = EXCLUDED.module_url,
             is_enabled = true,
             updated_at = NOW()`,
      [command, moduleName, moduleUrl, description, command, category, communityId]
    );
  }

  const redis = await getRedisClient();
  await redis.publish(
    'command:reload',
    JSON.stringify({ communityId, action: 'register', moduleId: module.id })
  );

  logger.audit('Marketplace commands registered', {
    communityId,
    moduleId: module.id,
    commands: module.trigger_commands,
  });
}

/**
 * Removes all commands registered for a marketplace module from the commands table.
 * @param {number} communityId
 * @param {number} moduleId
 */
export async function unregisterModuleCommands(communityId, moduleId) {
  const moduleName = 'marketplace:' + moduleId;

  await query(
    `DELETE FROM commands WHERE community_id = $1 AND module_name = $2`,
    [communityId, moduleName]
  );

  const redis = await getRedisClient();
  await redis.publish(
    'command:reload',
    JSON.stringify({ communityId, action: 'unregister', moduleId })
  );

  logger.audit('Marketplace commands unregistered', { communityId, moduleId });
}

/**
 * Returns all marketplace-registered commands for a community.
 * @param {number} communityId
 */
export async function getRegisteredCommands(communityId) {
  const result = await query(
    `SELECT * FROM commands WHERE community_id = $1 AND module_name LIKE 'marketplace:%'`,
    [communityId]
  );
  return result.rows;
}

export default {
  registerModuleCommands,
  unregisterModuleCommands,
  getRegisteredCommands,
};
