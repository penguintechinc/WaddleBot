/**
 * Analytics Controller - Platform-level analytics for superadmin
 * Aggregate queries on existing tables; no mutations.
 */
import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';
import { REPUTATION_TIERS } from '../utils/reputation.js';

/**
 * GET /api/v1/superadmin/analytics
 * Platform overview: summary stats, reputation tier distribution, platform breakdown
 */
export async function getPlatformOverview(req, res, next) {
  try {
    // Summary stats
    const summaryResult = await query(`
      SELECT
        (SELECT COUNT(*) FROM hub_users WHERE is_active = TRUE) AS total_users,
        (SELECT COUNT(*) FROM hub_users WHERE is_active = TRUE
           AND last_active_at >= NOW() - INTERVAL '30 days') AS active_users_30d,
        (SELECT COUNT(*) FROM communities WHERE is_active = TRUE AND is_global = FALSE) AS total_communities,
        (SELECT ROUND(AVG(platform_reputation)::numeric, 1)
           FROM platform_user_reputation) AS avg_platform_reputation
    `);
    const summary = summaryResult.rows[0];

    // Reputation tier distribution from the view
    const tierCases = REPUTATION_TIERS.map(
      t => `COUNT(*) FILTER (WHERE platform_reputation >= ${t.min} AND platform_reputation <= ${t.max}) AS ${t.shortLabel}`
    ).join(', ');
    const tierResult = await query(
      `SELECT ${tierCases}, COUNT(*) AS total FROM platform_user_reputation`
    );
    const tierRow = tierResult.rows[0];
    const reputationTiers = REPUTATION_TIERS.map(t => ({
      label: t.label,
      shortLabel: t.shortLabel,
      min: t.min,
      max: t.max,
      count: parseInt(tierRow[t.shortLabel] || 0, 10),
    }));

    // Platform breakdown (community platform types)
    const platformResult = await query(`
      SELECT platform, COUNT(*) AS count
      FROM communities
      WHERE is_active = TRUE AND is_global = FALSE
      GROUP BY platform
      ORDER BY count DESC
    `);

    // Community type distribution
    const typeResult = await query(`
      SELECT community_type, COUNT(*) AS count
      FROM communities
      WHERE is_active = TRUE AND is_global = FALSE
      GROUP BY community_type
      ORDER BY count DESC
    `);

    res.json({
      success: true,
      summary: {
        totalUsers: parseInt(summary.total_users, 10),
        activeUsers30d: parseInt(summary.active_users_30d, 10),
        totalCommunities: parseInt(summary.total_communities, 10),
        avgPlatformReputation: parseFloat(summary.avg_platform_reputation) || 0,
      },
      reputationTiers,
      platformBreakdown: platformResult.rows.map(r => ({
        platform: r.platform,
        count: parseInt(r.count, 10),
      })),
      communityTypes: typeResult.rows.map(r => ({
        type: r.community_type || 'unset',
        count: parseInt(r.count, 10),
      })),
    });
  } catch (err) {
    logger.error('Failed to load platform analytics overview', err);
    next(err);
  }
}

/**
 * GET /api/v1/superadmin/analytics/reputation
 * Detailed reputation distribution with stats
 */
export async function getReputationDistribution(req, res, next) {
  try {
    const statsResult = await query(`
      SELECT
        COUNT(*) AS total,
        ROUND(AVG(platform_reputation)::numeric, 1) AS avg,
        PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY platform_reputation) AS median,
        MIN(platform_reputation) AS min,
        MAX(platform_reputation) AS max
      FROM platform_user_reputation
    `);
    const stats = statsResult.rows[0];

    // Histogram buckets (50-point ranges)
    const bucketResult = await query(`
      SELECT
        FLOOR(platform_reputation / 50) * 50 AS bucket_min,
        FLOOR(platform_reputation / 50) * 50 + 49 AS bucket_max,
        COUNT(*) AS count
      FROM platform_user_reputation
      GROUP BY FLOOR(platform_reputation / 50)
      ORDER BY bucket_min
    `);

    res.json({
      success: true,
      stats: {
        total: parseInt(stats.total, 10),
        avg: parseFloat(stats.avg) || 0,
        median: parseFloat(stats.median) || 0,
        min: parseInt(stats.min, 10) || 0,
        max: parseInt(stats.max, 10) || 0,
      },
      histogram: bucketResult.rows.map(r => ({
        range: `${r.bucket_min}-${r.bucket_max}`,
        count: parseInt(r.count, 10),
      })),
    });
  } catch (err) {
    logger.error('Failed to load reputation distribution', err);
    next(err);
  }
}

/**
 * GET /api/v1/superadmin/analytics/growth?period=30d|90d|1y
 * Time-series: new users and communities per period bucket
 */
export async function getGrowthTrends(req, res, next) {
  try {
    const period = req.query.period || '90d';
    let interval, trunc;

    switch (period) {
      case '30d':
        interval = '30 days';
        trunc = 'day';
        break;
      case '1y':
        interval = '1 year';
        trunc = 'month';
        break;
      default: // 90d
        interval = '90 days';
        trunc = 'week';
        break;
    }

    const usersResult = await query(`
      SELECT DATE_TRUNC($1, created_at) AS period,
             COUNT(*) AS count
      FROM hub_users
      WHERE created_at >= NOW() - $2::interval
      GROUP BY DATE_TRUNC($1, created_at)
      ORDER BY period
    `, [trunc, interval]);

    const communitiesResult = await query(`
      SELECT DATE_TRUNC($1, created_at) AS period,
             COUNT(*) AS count
      FROM communities
      WHERE created_at >= NOW() - $2::interval
        AND is_global = FALSE
      GROUP BY DATE_TRUNC($1, created_at)
      ORDER BY period
    `, [trunc, interval]);

    res.json({
      success: true,
      period,
      truncation: trunc,
      users: usersResult.rows.map(r => ({
        period: r.period,
        count: parseInt(r.count, 10),
      })),
      communities: communitiesResult.rows.map(r => ({
        period: r.period,
        count: parseInt(r.count, 10),
      })),
    });
  } catch (err) {
    logger.error('Failed to load growth trends', err);
    next(err);
  }
}

/**
 * GET /api/v1/superadmin/analytics/activity
 * Active user segments: 24h, 7d, 30d, 90d, inactive
 */
export async function getActivityBreakdown(req, res, next) {
  try {
    const result = await query(`
      SELECT
        COUNT(*) FILTER (WHERE last_active_at >= NOW() - INTERVAL '24 hours') AS active_24h,
        COUNT(*) FILTER (WHERE last_active_at >= NOW() - INTERVAL '7 days'
                           AND last_active_at < NOW() - INTERVAL '24 hours') AS active_7d,
        COUNT(*) FILTER (WHERE last_active_at >= NOW() - INTERVAL '30 days'
                           AND last_active_at < NOW() - INTERVAL '7 days') AS active_30d,
        COUNT(*) FILTER (WHERE last_active_at >= NOW() - INTERVAL '90 days'
                           AND last_active_at < NOW() - INTERVAL '30 days') AS active_90d,
        COUNT(*) FILTER (WHERE last_active_at < NOW() - INTERVAL '90 days'
                           OR last_active_at IS NULL) AS inactive,
        COUNT(*) AS total
      FROM hub_users
      WHERE is_active = TRUE
    `);
    const row = result.rows[0];

    res.json({
      success: true,
      segments: [
        { label: 'Active (24h)', key: 'active_24h', count: parseInt(row.active_24h, 10) },
        { label: 'Active (7d)', key: 'active_7d', count: parseInt(row.active_7d, 10) },
        { label: 'Active (30d)', key: 'active_30d', count: parseInt(row.active_30d, 10) },
        { label: 'Active (90d)', key: 'active_90d', count: parseInt(row.active_90d, 10) },
        { label: 'Inactive', key: 'inactive', count: parseInt(row.inactive, 10) },
      ],
      total: parseInt(row.total, 10),
    });
  } catch (err) {
    logger.error('Failed to load activity breakdown', err);
    next(err);
  }
}
