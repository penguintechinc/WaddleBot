/**
 * Vendor Analytics Controller — analytics endpoints for vendor dashboard
 */
import * as analyticsService from '../services/vendorAnalyticsService.js';

/**
 * GET /vendor/analytics/sales
 * Returns sales and installation metrics for the authenticated vendor.
 * Query params: period (7d | 30d | 90d | mtd | ytd | all)
 */
export async function getSalesMetrics(req, res, next) {
  try {
    const { period = '30d' } = req.query;
    const data = await analyticsService.getSalesMetrics(req.user.id, { period });
    if (!data) {
      return res.status(404).json({ success: false, error: 'Vendor profile not found' });
    }
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/analytics/installs
 * Returns a time series of install and uninstall counts for charting.
 * Query params: period (7d | 30d | 90d | ytd | all), granularity (day | week | month)
 */
export async function getInstallTimeSeries(req, res, next) {
  try {
    const { period = '30d', granularity = 'day' } = req.query;
    const data = await analyticsService.getInstallTimeSeries(req.user.id, { period, granularity });
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/analytics/api-usage
 * Returns API usage metrics (placeholder until request tracking is implemented).
 * Query params: period (7d | 30d | 90d | mtd | ytd | all)
 */
export async function getApiUsageMetrics(req, res, next) {
  try {
    const { period = '30d' } = req.query;
    const data = await analyticsService.getApiUsageMetrics(req.user.id, { period });
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/analytics/discount-codes
 * Returns per-code redemption stats, revenue impact, and active/expired counts.
 */
export async function getDiscountCodePerformance(req, res, next) {
  try {
    const data = await analyticsService.getDiscountCodePerformance(req.user.id);
    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/analytics/communities
 * Returns a paginated per-community installation breakdown.
 * Query params: moduleId, page, limit, sortBy (installed_at | status | last_active)
 */
export async function getCommunityDrilldown(req, res, next) {
  try {
    const {
      moduleId,
      page = '1',
      limit = '25',
      sortBy = 'installed_at',
    } = req.query;

    const parsedPage = Math.max(1, parseInt(page, 10) || 1);
    const parsedLimit = Math.min(100, Math.max(1, parseInt(limit, 10) || 25));
    const parsedModuleId = moduleId ? parseInt(moduleId, 10) : null;

    if (moduleId && (isNaN(parsedModuleId) || parsedModuleId <= 0)) {
      return res.status(400).json({ success: false, error: 'Invalid moduleId' });
    }

    const data = await analyticsService.getCommunityDrilldown(req.user.id, {
      moduleId: parsedModuleId,
      page: parsedPage,
      limit: parsedLimit,
      sortBy,
    });

    res.json({ success: true, data });
  } catch (err) {
    next(err);
  }
}

/**
 * GET /vendor/analytics/export
 * Streams a CSV download for the requested analytics type and period.
 * Query params: type (sales | installs), period (7d | 30d | 90d | mtd | ytd | all)
 */
export async function exportCsv(req, res, next) {
  try {
    const { type = 'sales', period = '30d' } = req.query;

    const validTypes = ['sales', 'installs'];
    if (!validTypes.includes(type)) {
      return res.status(400).json({ success: false, error: `Invalid type. Must be one of: ${validTypes.join(', ')}` });
    }

    const { csv, filename } = await analyticsService.exportAnalyticsCsv(req.user.id, { type, period });

    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    res.send(csv);
  } catch (err) {
    next(err);
  }
}
