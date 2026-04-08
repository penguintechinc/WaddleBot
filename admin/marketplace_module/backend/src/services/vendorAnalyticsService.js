/**
 * Vendor Analytics Service — sales metrics, install time series, API usage,
 * discount code performance, community drilldown, and CSV export.
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';

/**
 * Resolves a period string to a SQL interval or date truncation expression.
 * Returns { whereClause, intervalLabel } for use in queries.
 * @param {string} period — '7d' | '30d' | '90d' | 'mtd' | 'ytd' | 'all'
 * @returns {{ sinceExpr: string, params: any[] }}
 */
function periodToSinceExpr(period) {
  switch (period) {
    case '7d':
      return { sinceExpr: `NOW() - INTERVAL '7 days'`, params: [] };
    case '30d':
      return { sinceExpr: `NOW() - INTERVAL '30 days'`, params: [] };
    case '90d':
      return { sinceExpr: `NOW() - INTERVAL '90 days'`, params: [] };
    case 'mtd':
      return { sinceExpr: `DATE_TRUNC('month', NOW())`, params: [] };
    case 'ytd':
      return { sinceExpr: `DATE_TRUNC('year', NOW())`, params: [] };
    case 'all':
    default:
      return { sinceExpr: null, params: [] };
  }
}

/**
 * Returns overall sales and installation metrics for a vendor.
 * @param {number} userId
 * @param {{ period?: string }} options
 */
export async function getSalesMetrics(userId, { period = '30d' } = {}) {
  // Fetch seller id for this user
  const sellerResult = await query(
    `SELECT id FROM marketplace_sellers WHERE user_id = $1 LIMIT 1`,
    [userId]
  );
  if (!sellerResult.rows[0]) {
    return null;
  }
  const sellerId = sellerResult.rows[0].id;

  const { sinceExpr } = periodToSinceExpr(period);
  const periodFilter = sinceExpr ? `AND cvi.installed_at >= ${sinceExpr}` : '';
  const uninstallPeriodFilter = sinceExpr ? `AND cvi.uninstalled_at >= ${sinceExpr}` : '';

  const [installsResult, uninstallsResult, activeResult, revenueResult, mtdRevenueResult, ytdRevenueResult] =
    await Promise.all([
      // Total installs in period
      query(
        `SELECT COUNT(*) AS count
         FROM community_vendor_installations cvi
         JOIN marketplace_modules mm ON mm.id = cvi.module_id
         WHERE mm.seller_id = $1 ${periodFilter}`,
        [sellerId]
      ),
      // Uninstalls in period
      query(
        `SELECT COUNT(*) AS count
         FROM community_vendor_installations cvi
         JOIN marketplace_modules mm ON mm.id = cvi.module_id
         WHERE mm.seller_id = $1
           AND cvi.status = 'uninstalled'
           AND cvi.uninstalled_at IS NOT NULL
           ${uninstallPeriodFilter}`,
        [sellerId]
      ),
      // Currently active installations
      query(
        `SELECT COUNT(*) AS count
         FROM community_vendor_installations cvi
         JOIN marketplace_modules mm ON mm.id = cvi.module_id
         WHERE mm.seller_id = $1 AND cvi.status = 'active'`,
        [sellerId]
      ),
      // Total revenue all-time
      query(
        `SELECT COALESCE(SUM(amount_cents), 0) AS total_cents
         FROM vendor_payments
         WHERE seller_id = $1 AND status = 'completed'`,
        [sellerId]
      ),
      // Revenue MTD
      query(
        `SELECT COALESCE(SUM(amount_cents), 0) AS total_cents
         FROM vendor_payments
         WHERE seller_id = $1
           AND status = 'completed'
           AND created_at >= DATE_TRUNC('month', NOW())`,
        [sellerId]
      ),
      // Revenue YTD
      query(
        `SELECT COALESCE(SUM(amount_cents), 0) AS total_cents
         FROM vendor_payments
         WHERE seller_id = $1
           AND status = 'completed'
           AND created_at >= DATE_TRUNC('year', NOW())`,
        [sellerId]
      ),
    ]);

  // New installs: today / this week / MTD / YTD
  const [todayResult, weekResult, mtdInstallsResult, ytdInstallsResult] = await Promise.all([
    query(
      `SELECT COUNT(*) AS count
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $1
         AND cvi.installed_at >= DATE_TRUNC('day', NOW())`,
      [sellerId]
    ),
    query(
      `SELECT COUNT(*) AS count
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $1
         AND cvi.installed_at >= DATE_TRUNC('week', NOW())`,
      [sellerId]
    ),
    query(
      `SELECT COUNT(*) AS count
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $1
         AND cvi.installed_at >= DATE_TRUNC('month', NOW())`,
      [sellerId]
    ),
    query(
      `SELECT COUNT(*) AS count
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $1
         AND cvi.installed_at >= DATE_TRUNC('year', NOW())`,
      [sellerId]
    ),
  ]);

  const totalInstalls = parseInt(installsResult.rows[0].count, 10);
  const uninstalls = parseInt(uninstallsResult.rows[0].count, 10);
  const churnRate = totalInstalls > 0 ? ((uninstalls / totalInstalls) * 100).toFixed(2) : '0.00';

  return {
    period,
    installations: {
      total: totalInstalls,
      active: parseInt(activeResult.rows[0].count, 10),
      uninstalls,
      churnRate: parseFloat(churnRate),
      new: {
        today: parseInt(todayResult.rows[0].count, 10),
        thisWeek: parseInt(weekResult.rows[0].count, 10),
        mtd: parseInt(mtdInstallsResult.rows[0].count, 10),
        ytd: parseInt(ytdInstallsResult.rows[0].count, 10),
      },
    },
    revenue: {
      totalCents: parseInt(revenueResult.rows[0].total_cents, 10),
      mtdCents: parseInt(mtdRevenueResult.rows[0].total_cents, 10),
      ytdCents: parseInt(ytdRevenueResult.rows[0].total_cents, 10),
    },
  };
}

/**
 * Returns a time series of daily/weekly/monthly install and uninstall counts.
 * @param {number} userId
 * @param {{ period?: string, granularity?: string }} options
 */
export async function getInstallTimeSeries(userId, { period = '30d', granularity = 'day' } = {}) {
  const sellerResult = await query(
    `SELECT id FROM marketplace_sellers WHERE user_id = $1 LIMIT 1`,
    [userId]
  );
  if (!sellerResult.rows[0]) {
    return [];
  }
  const sellerId = sellerResult.rows[0].id;

  const validGranularities = ['day', 'week', 'month'];
  const safeGranularity = validGranularities.includes(granularity) ? granularity : 'day';

  const { sinceExpr } = periodToSinceExpr(period);
  const sinceFilter = sinceExpr ? `AND series_date >= ${sinceExpr}` : '';

  // Build a complete date series joined with actual counts to fill gaps with zeros
  const result = await query(
    `WITH date_series AS (
       SELECT DATE_TRUNC($1, d) AS series_date
       FROM generate_series(
         COALESCE(
           (SELECT MIN(DATE_TRUNC($1, cvi.installed_at))
            FROM community_vendor_installations cvi
            JOIN marketplace_modules mm ON mm.id = cvi.module_id
            WHERE mm.seller_id = $2
            ${sinceFilter.replace('series_date', `DATE_TRUNC($1, cvi.installed_at)`)}
           ),
           NOW() - INTERVAL '30 days'
         ),
         NOW(),
         ('1 ' || $1)::INTERVAL
       ) AS d
     ),
     installs_agg AS (
       SELECT DATE_TRUNC($1, cvi.installed_at) AS bucket, COUNT(*) AS installs
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $2
         ${sinceFilter.replace('series_date', `DATE_TRUNC($1, cvi.installed_at)`)}
       GROUP BY bucket
     ),
     uninstalls_agg AS (
       SELECT DATE_TRUNC($1, cvi.uninstalled_at) AS bucket, COUNT(*) AS uninstalls
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $2
         AND cvi.status = 'uninstalled'
         AND cvi.uninstalled_at IS NOT NULL
         ${sinceFilter.replace('series_date', `DATE_TRUNC($1, cvi.uninstalled_at)`)}
       GROUP BY bucket
     )
     SELECT
       ds.series_date AS date,
       COALESCE(ia.installs, 0)::int AS installs,
       COALESCE(ua.uninstalls, 0)::int AS uninstalls
     FROM date_series ds
     LEFT JOIN installs_agg ia ON ia.bucket = ds.series_date
     LEFT JOIN uninstalls_agg ua ON ua.bucket = ds.series_date
     ORDER BY ds.series_date ASC`,
    [safeGranularity, sellerId]
  );

  return result.rows.map((row) => ({
    date: row.date,
    installs: row.installs,
    uninstalls: row.uninstalls,
  }));
}

/**
 * Returns API usage metrics for the vendor.
 * Actual per-request tracking is not yet implemented; returns a placeholder structure.
 * @param {number} userId
 * @param {{ period?: string }} options
 */
export async function getApiUsageMetrics(userId, { period = '30d' } = {}) {
  logger.debug({ userId, period }, 'getApiUsageMetrics: returning placeholder data');

  return {
    period,
    placeholder: true,
    totalRequests: 0,
    requestsPerDay: [],
    errorRate: 0,
    avgResponseTimeMs: 0,
    message: 'Per-request API tracking not yet implemented.',
  };
}

/**
 * Returns per-discount-code redemption stats, revenue impact, and active/expired counts.
 * @param {number} userId
 */
export async function getDiscountCodePerformance(userId) {
  const sellerResult = await query(
    `SELECT id FROM marketplace_sellers WHERE user_id = $1 LIMIT 1`,
    [userId]
  );
  if (!sellerResult.rows[0]) {
    return { codes: [], summary: { active: 0, expired: 0 } };
  }
  const sellerId = sellerResult.rows[0].id;

  const [codesResult, summaryResult] = await Promise.all([
    query(
      `SELECT
         dc.id,
         dc.code,
         dc.discount_type,
         dc.discount_value,
         dc.is_active,
         dc.valid_from,
         dc.valid_until,
         dc.max_uses,
         dc.current_uses,
         COALESCE(redemption_stats.total_redemptions, 0) AS total_redemptions,
         COALESCE(redemption_stats.total_discount_cents, 0) AS total_discount_cents,
         COALESCE(redemption_stats.unique_communities, 0) AS unique_communities
       FROM vendor_discount_codes dc
       JOIN marketplace_modules mm ON mm.id = dc.module_id
       LEFT JOIN (
         SELECT
           r.discount_code_id,
           COUNT(*) AS total_redemptions,
           SUM(r.discount_amount_cents) AS total_discount_cents,
           COUNT(DISTINCT r.community_id) AS unique_communities
         FROM discount_code_redemptions r
         GROUP BY r.discount_code_id
       ) redemption_stats ON redemption_stats.discount_code_id = dc.id
       WHERE mm.seller_id = $1
       ORDER BY total_redemptions DESC`,
      [sellerId]
    ),
    query(
      `SELECT
         SUM(CASE WHEN
           dc.is_active = true
           AND (dc.valid_from IS NULL OR dc.valid_from <= NOW())
           AND (dc.valid_until IS NULL OR dc.valid_until >= NOW())
           AND (dc.max_uses IS NULL OR dc.current_uses < dc.max_uses)
           THEN 1 ELSE 0 END) AS active_count,
         SUM(CASE WHEN
           dc.is_active = false
           OR (dc.valid_until IS NOT NULL AND dc.valid_until < NOW())
           OR (dc.max_uses IS NOT NULL AND dc.current_uses >= dc.max_uses)
           THEN 1 ELSE 0 END) AS expired_count
       FROM vendor_discount_codes dc
       JOIN marketplace_modules mm ON mm.id = dc.module_id
       WHERE mm.seller_id = $1`,
      [sellerId]
    ),
  ]);

  const codes = codesResult.rows.map((row) => {
    const conversionRate =
      row.max_uses && row.max_uses > 0
        ? ((row.total_redemptions / row.max_uses) * 100).toFixed(2)
        : null;
    return {
      id: row.id,
      code: row.code,
      discountType: row.discount_type,
      discountValue: row.discount_value,
      isActive: row.is_active,
      validFrom: row.valid_from,
      validUntil: row.valid_until,
      maxUses: row.max_uses,
      currentUses: row.current_uses,
      totalRedemptions: parseInt(row.total_redemptions, 10),
      totalDiscountCents: parseInt(row.total_discount_cents, 10),
      uniqueCommunities: parseInt(row.unique_communities, 10),
      conversionRate: conversionRate !== null ? parseFloat(conversionRate) : null,
    };
  });

  return {
    codes,
    summary: {
      active: parseInt(summaryResult.rows[0]?.active_count ?? 0, 10),
      expired: parseInt(summaryResult.rows[0]?.expired_count ?? 0, 10),
    },
  };
}

/**
 * Returns a paginated per-community breakdown of installations for a vendor.
 * @param {number} userId
 * @param {{ moduleId?: number, page?: number, limit?: number, sortBy?: string }} options
 */
export async function getCommunityDrilldown(
  userId,
  { moduleId = null, page = 1, limit = 25, sortBy = 'installed_at' } = {}
) {
  const sellerResult = await query(
    `SELECT id FROM marketplace_sellers WHERE user_id = $1 LIMIT 1`,
    [userId]
  );
  if (!sellerResult.rows[0]) {
    return { rows: [], total: 0, page, limit };
  }
  const sellerId = sellerResult.rows[0].id;

  const validSortColumns = {
    installed_at: 'cvi.installed_at',
    status: 'cvi.status',
    last_active: 'cvi.last_active_at',
  };
  const orderCol = validSortColumns[sortBy] ?? 'cvi.installed_at';
  const offset = (page - 1) * limit;

  const moduleFilter = moduleId ? `AND cvi.module_id = $4` : '';
  const params = moduleId
    ? [sellerId, limit, offset, moduleId]
    : [sellerId, limit, offset];

  const [rowsResult, countResult] = await Promise.all([
    query(
      `SELECT
         cvi.id AS installation_id,
         cvi.community_id,
         cvi.module_id,
         mm.name AS module_name,
         cvi.status,
         cvi.installed_at,
         cvi.uninstalled_at,
         cvi.last_active_at,
         dc.code AS discount_code_used
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       LEFT JOIN vendor_discount_codes dc ON dc.id = cvi.discount_code_id
       WHERE mm.seller_id = $1
         ${moduleFilter}
       ORDER BY ${orderCol} DESC
       LIMIT $2 OFFSET $3`,
      params
    ),
    query(
      `SELECT COUNT(*) AS total
       FROM community_vendor_installations cvi
       JOIN marketplace_modules mm ON mm.id = cvi.module_id
       WHERE mm.seller_id = $1
         ${moduleFilter}`,
      moduleId ? [sellerId, moduleId] : [sellerId]
    ),
  ]);

  return {
    rows: rowsResult.rows,
    total: parseInt(countResult.rows[0].total, 10),
    page,
    limit,
  };
}

/**
 * Generates a CSV string for the requested analytics type and period.
 * @param {number} userId
 * @param {{ type?: string, period?: string }} options
 * @returns {Promise<{ csv: string, filename: string }>}
 */
export async function exportAnalyticsCsv(userId, { type = 'sales', period = '30d' } = {}) {
  if (type === 'installs') {
    const series = await getInstallTimeSeries(userId, { period, granularity: 'day' });
    const header = 'date,installs,uninstalls\n';
    const body = series
      .map((r) => `${new Date(r.date).toISOString().split('T')[0]},${r.installs},${r.uninstalls}`)
      .join('\n');
    return {
      csv: header + body,
      filename: `install-timeseries-${period}.csv`,
    };
  }

  // Default: sales / revenue summary
  const metrics = await getSalesMetrics(userId, { period });
  if (!metrics) {
    return { csv: 'metric,value\n', filename: `sales-${period}.csv` };
  }

  const rows = [
    ['metric', 'value'],
    ['period', period],
    ['total_installations', metrics.installations.total],
    ['active_installations', metrics.installations.active],
    ['uninstalls', metrics.installations.uninstalls],
    ['churn_rate_pct', metrics.installations.churnRate],
    ['new_installs_today', metrics.installations.new.today],
    ['new_installs_this_week', metrics.installations.new.thisWeek],
    ['new_installs_mtd', metrics.installations.new.mtd],
    ['new_installs_ytd', metrics.installations.new.ytd],
    ['total_revenue_cents', metrics.revenue.totalCents],
    ['mtd_revenue_cents', metrics.revenue.mtdCents],
    ['ytd_revenue_cents', metrics.revenue.ytdCents],
  ];

  const csv = rows.map((r) => r.join(',')).join('\n');
  return { csv, filename: `sales-metrics-${period}.csv` };
}
