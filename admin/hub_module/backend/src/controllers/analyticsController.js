/**
 * Analytics Controller - Proxies to analytics-core module
 * Hub is the auth boundary. Analytics-core returns aggregate data only.
 */
import * as analyticsService from '../services/analyticsService.js';
import { logger } from '../utils/logger.js';

export async function getPlatformOverview(req, res, next) {
  try {
    const [summary, tiers, activity] = await Promise.all([
      analyticsService.getPlatformSummary(),
      analyticsService.getReputationDistribution(),
      analyticsService.getActivityBreakdown(),
    ]);
    // Maintain existing response shape for backward compat with superadmin frontend
    const s = summary.data || summary;
    const t = tiers.data || tiers;
    res.json({
      success: true,
      summary: s.summary || s,
      reputationTiers: t.histogram || [],
      platformBreakdown: [],
      communityTypes: [],
    });
  } catch (err) {
    logger.error('Failed to load platform analytics overview', err);
    next(err);
  }
}

export async function getReputationDistribution(req, res, next) {
  try {
    const data = await analyticsService.getReputationDistribution();
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load reputation distribution', err);
    next(err);
  }
}

export async function getGrowthTrends(req, res, next) {
  try {
    const period = req.query.period || '90d';
    const data = await analyticsService.getGrowthTrends(period);
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load growth trends', err);
    next(err);
  }
}

export async function getActivityBreakdown(req, res, next) {
  try {
    const data = await analyticsService.getActivityBreakdown();
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load activity breakdown', err);
    next(err);
  }
}

export async function getCommunityHealthSummaries(req, res, next) {
  try {
    const limit = Math.min(200, Math.max(1, parseInt(req.query.limit || '50', 10)));
    const data = await analyticsService.getCommunityHealthSummaries(limit);
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load community health summaries', err);
    next(err);
  }
}

export async function getUserSelfStats(req, res, next) {
  try {
    const hubUserId = req.params.userId ? parseInt(req.params.userId, 10) : req.user.userId;
    const data = await analyticsService.getUserSelfStats(hubUserId, req.user.userId, req.user.isSuperAdmin ? 'superadmin' : 'user');
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load user self stats', err);
    next(err);
  }
}

export async function getUserCommunityStats(req, res, next) {
  try {
    const hubUserId = parseInt(req.params.userId, 10);
    const communityId = parseInt(req.params.communityId, 10);
    const data = await analyticsService.getUserCommunityStats(hubUserId, communityId, req.user.userId, 'community_admin');
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load user community stats', err);
    next(err);
  }
}

export async function getUserReputation(req, res, next) {
  try {
    // Works for both self (/me/reputation) and admin (/users/:userId/reputation)
    const hubUserId = req.params.userId ? parseInt(req.params.userId, 10) : req.user.userId;
    const data = await analyticsService.getUserReputation(hubUserId, req.user.userId, req.user.isSuperAdmin ? 'superadmin' : 'user');
    res.json({ success: true, ...(data.data || data) });
  } catch (err) {
    logger.error('Failed to load user reputation', err);
    next(err);
  }
}
