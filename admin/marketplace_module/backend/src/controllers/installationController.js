/**
 * Installation Controller — community module install/uninstall/list
 */
import * as installationService from '../services/installationService.js';
import { errors } from '../middleware/errorHandler.js';

/**
 * GET /communities/:communityId/installed
 * Returns all installed modules for a community.
 */
export async function getInstalledModules(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const installed = await installationService.getInstalledModules(communityId);
    res.json({ success: true, installed, total: installed.length });
  } catch (err) {
    next(err);
  }
}

/**
 * POST /communities/:communityId/install
 * Installs a module for a community.
 * Body: { source, moduleId }
 */
export async function installModule(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { source, moduleId } = req.body;

    if (!source || !['core', 'marketplace'].includes(source)) {
      return next(errors.badRequest('source must be core or marketplace'));
    }

    const parsedModuleId = parseInt(moduleId, 10);
    if (!parsedModuleId || parsedModuleId <= 0) {
      return next(errors.badRequest('moduleId must be a positive integer'));
    }

    const installation = await installationService.installModule(
      communityId,
      source,
      parsedModuleId,
      req.user.id
    );

    res.status(201).json({ success: true, message: 'Module installed', installation });
  } catch (err) {
    next(err);
  }
}

/**
 * DELETE /communities/:communityId/install/:moduleId
 * Uninstalls a module from a community.
 * Query param: source (default 'core')
 */
export async function uninstallModule(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const moduleId = parseInt(req.params.moduleId, 10);
    const source = req.query.source || 'core';

    await installationService.uninstallModule(communityId, source, moduleId);

    res.json({ success: true, message: 'Module uninstalled' });
  } catch (err) {
    next(err);
  }
}

/**
 * PUT /communities/:communityId/install/:moduleId
 * Enables or disables an installed module.
 * Body: { source, isEnabled }
 */
export async function toggleModule(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const moduleId = parseInt(req.params.moduleId, 10);
    const { source, isEnabled } = req.body;

    await installationService.toggleModule(communityId, source, moduleId, isEnabled);

    res.json({ success: true, message: 'Module updated' });
  } catch (err) {
    next(err);
  }
}

export default {
  getInstalledModules,
  installModule,
  uninstallModule,
  toggleModule,
};
