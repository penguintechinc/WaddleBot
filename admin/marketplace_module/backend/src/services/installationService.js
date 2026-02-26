/**
 * Installation Service — community module install/uninstall
 * Handles both core hub_modules and marketplace vendor modules.
 */
import { query, transaction } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';
import * as commandRegistrationService from './commandRegistrationService.js';

/**
 * Returns all installed modules (both core and marketplace) for a community.
 * @param {number} communityId
 */
export async function getInstalledModules(communityId) {
  const result = await query(
    `SELECT
       'core' AS source,
       hmi.id AS installation_id,
       hm.id AS source_id,
       hm.name,
       COALESCE(hm.display_name, hm.name) AS display_name,
       hm.description,
       hm.category,
       hm.icon_url,
       hm.version,
       hmi.is_enabled,
       hmi.config,
       hmi.installed_at,
       hmi.updated_at
     FROM hub_module_installations hmi
     JOIN hub_modules hm ON hm.id = hmi.module_id
     WHERE hmi.community_id = $1
     UNION ALL
     SELECT
       'marketplace' AS source,
       ms.id AS installation_id,
       mm.id AS source_id,
       mm.name,
       mm.name AS display_name,
       mm.description,
       mm.category,
       mm.icon_url,
       mm.version,
       ms.is_enabled,
       '{}'::jsonb AS config,
       ms.subscribed_at AS installed_at,
       ms.subscribed_at AS updated_at
     FROM marketplace_subscriptions ms
     JOIN marketplace_modules mm ON mm.id = ms.module_id
     WHERE ms.community_id = $1 AND ms.status = 'active'
     ORDER BY installed_at DESC`,
    [communityId]
  );

  return result.rows.map((row) => ({
    source: row.source,
    installationId: row.installation_id,
    sourceId: row.source_id,
    name: row.name,
    displayName: row.display_name,
    description: row.description,
    category: row.category,
    iconUrl: row.icon_url,
    version: row.version,
    isEnabled: row.is_enabled,
    config: row.config,
    installedAt: row.installed_at,
    updatedAt: row.updated_at,
  }));
}

/**
 * Installs a module (core or marketplace) for a community.
 * @param {number} communityId
 * @param {string} source - 'core' or 'marketplace'
 * @param {number} moduleId
 * @param {number} installedBy - userId
 */
export async function installModule(communityId, source, moduleId, installedBy) {
  if (source === 'core') {
    let installationId;
    try {
      const result = await query(
        `INSERT INTO hub_module_installations (community_id, module_id, installed_by, is_enabled)
         VALUES ($1, $2, $3, true)
         RETURNING id`,
        [communityId, moduleId, installedBy]
      );
      installationId = result.rows[0].id;
    } catch (err) {
      if (err.code === '23505') {
        throw errors.conflict('Module already installed');
      }
      throw err;
    }

    logger.audit('Core module installed', { communityId, moduleId, installedBy });
    return { installationId, source: 'core', moduleId, communityId };
  }

  if (source === 'marketplace') {
    const moduleResult = await query(
      `SELECT * FROM marketplace_modules
       WHERE id = $1 AND status = 'approved' AND deleted_at IS NULL`,
      [moduleId]
    );

    if (moduleResult.rows.length === 0) {
      throw errors.notFound('Module not found or not approved');
    }

    const module = moduleResult.rows[0];
    let installationId;

    try {
      const result = await transaction(async (client) => {
        await commandRegistrationService.registerModuleCommands(communityId, module);

        const insertResult = await client.query(
          `INSERT INTO marketplace_subscriptions
             (community_id, module_id, status, is_enabled, subscribed_at)
           VALUES ($1, $2, 'active', true, NOW())
           RETURNING id`,
          [communityId, moduleId]
        );
        return insertResult;
      });
      installationId = result.rows[0].id;
    } catch (err) {
      if (err.code === '23505') {
        throw errors.conflict('Module already installed');
      }
      throw err;
    }

    logger.audit('Marketplace module installed', { communityId, moduleId, installedBy });
    return { installationId, source: 'marketplace', moduleId, communityId };
  }

  throw errors.badRequest('Invalid source: must be core or marketplace');
}

/**
 * Uninstalls a module from a community.
 * @param {number} communityId
 * @param {string} source - 'core' or 'marketplace'
 * @param {number} moduleId
 */
export async function uninstallModule(communityId, source, moduleId) {
  if (source === 'core') {
    const result = await query(
      `DELETE FROM hub_module_installations
       WHERE community_id = $1 AND module_id = $2
       RETURNING id`,
      [communityId, moduleId]
    );

    if (result.rows.length === 0) {
      throw errors.notFound('Module not installed');
    }

    logger.audit('Core module uninstalled', { communityId, moduleId });
    return { success: true };
  }

  if (source === 'marketplace') {
    await commandRegistrationService.unregisterModuleCommands(communityId, moduleId);

    const result = await query(
      `UPDATE marketplace_subscriptions
       SET status = 'canceled', canceled_at = NOW()
       WHERE community_id = $1 AND module_id = $2
       RETURNING id`,
      [communityId, moduleId]
    );

    if (result.rows.length === 0) {
      throw errors.notFound('Module not installed');
    }

    logger.audit('Marketplace module uninstalled', { communityId, moduleId });
    return { success: true };
  }

  throw errors.badRequest('Invalid source: must be core or marketplace');
}

/**
 * Enables or disables an installed module for a community.
 * @param {number} communityId
 * @param {string} source - 'core' or 'marketplace'
 * @param {number} moduleId
 * @param {boolean} isEnabled
 */
export async function toggleModule(communityId, source, moduleId, isEnabled) {
  if (source === 'core') {
    await query(
      `UPDATE hub_module_installations
       SET is_enabled = $3, updated_at = NOW()
       WHERE community_id = $1 AND module_id = $2`,
      [communityId, moduleId, isEnabled]
    );
  } else if (source === 'marketplace') {
    await query(
      `UPDATE marketplace_subscriptions
       SET is_enabled = $3
       WHERE community_id = $1 AND module_id = $2 AND status = 'active'`,
      [communityId, moduleId, isEnabled]
    );
  } else {
    throw errors.badRequest('Invalid source: must be core or marketplace');
  }

  return { success: true };
}

export default {
  getInstalledModules,
  installModule,
  uninstallModule,
  toggleModule,
};
