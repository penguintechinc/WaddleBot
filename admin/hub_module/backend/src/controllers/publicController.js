/**
 * Public Controller - No authentication required
 */
import { query } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';

/**
 * Get platform statistics
 */
export async function getStats(req, res, next) {
  try {
    // Get community count
    const communitiesResult = await query(
      'SELECT COUNT(*) as count FROM communities WHERE is_active = true'
    );

    // Initialize stats with defaults
    const stats = {
      communities: parseInt(communitiesResult.rows[0]?.count || 0, 10),
      discord: { servers: 0, channels: 0 },
      twitch: { channels: 0, live: 0, viewers: 0 },
      slack: { workspaces: 0, channels: 0 },
    };

    // Try to get platform counts from coordination table
    // This may fail if the table doesn't exist or has wrong schema
    try {
      const platformResult = await query(`
        SELECT
          platform,
          COUNT(DISTINCT server_id) as servers,
          COUNT(*) as channels,
          SUM(CASE WHEN is_live = true THEN 1 ELSE 0 END) as live,
          SUM(CASE WHEN is_live = true THEN viewer_count ELSE 0 END) as viewers
        FROM coordination
        WHERE platform IS NOT NULL
        GROUP BY platform
      `);

      for (const row of platformResult.rows) {
        switch (row.platform) {
          case 'discord':
            stats.discord = {
              servers: parseInt(row.servers || 0, 10),
              channels: parseInt(row.channels || 0, 10),
            };
            break;
          case 'twitch':
            stats.twitch = {
              channels: parseInt(row.channels || 0, 10),
              live: parseInt(row.live || 0, 10),
              viewers: parseInt(row.viewers || 0, 10),
            };
            break;
          case 'slack':
            stats.slack = {
              workspaces: parseInt(row.servers || 0, 10),
              channels: parseInt(row.channels || 0, 10),
            };
            break;
        }
      }
    } catch (coordErr) {
      // Log the error but return stats with zeros instead of failing
      console.error('Failed to fetch coordination stats:', coordErr.message);
      // Stats already initialized with zeros above
    }

    res.json({ success: true, stats });
  } catch (err) {
    next(err);
  }
}

/**
 * Get spotlighted communities (top active, public, non-support)
 */
export async function getSpotlightedCommunities(req, res, next) {
  try {
    const result = await query(`
      SELECT id, name, display_name, description, platform,
             community_type, member_count, config, created_at
      FROM communities
      WHERE is_active = true AND is_public = true
        AND (community_type IS NULL OR community_type != 'support')
      ORDER BY member_count DESC, created_at DESC
      LIMIT 5
    `);

    const communities = result.rows.map(row => ({
      id: row.id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      logoUrl: row.config?.logo_url || null,
      platform: row.platform,
      communityType: row.community_type || 'creator',
      memberCount: row.member_count || 0,
    }));

    res.json({ success: true, communities });
  } catch (err) {
    next(err);
  }
}

/**
 * List public communities
 */
export async function getCommunities(req, res, next) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '12', 10)));
    const offset = (page - 1) * limit;

    // Get total count
    const countResult = await query(
      'SELECT COUNT(*) as count FROM communities WHERE is_active = true AND is_public = true'
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    // Get communities
    const result = await query(`
      SELECT id, name, display_name, description, platform,
             member_count, config, created_at
      FROM communities
      WHERE is_active = true AND is_public = true
      ORDER BY member_count DESC, name ASC
      LIMIT $1 OFFSET $2
    `, [limit, offset]);

    const communities = result.rows.map(row => ({
      id: row.id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      logoUrl: row.config?.logo_url || null,
      platform: row.platform,
      memberCount: row.member_count || 0,
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({
      success: true,
      communities,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get single community public info
 */
export async function getCommunity(req, res, next) {
  try {
    const communityId = parseInt(req.params.id, 10);

    if (isNaN(communityId)) {
      return next(errors.badRequest('Invalid community ID'));
    }

    const result = await query(`
      SELECT id, name, display_name, description, platform,
             member_count, config, join_mode, created_at
      FROM communities
      WHERE id = $1 AND is_active = true AND is_public = true
    `, [communityId]);

    if (result.rows.length === 0) {
      return next(errors.notFound('Community not found'));
    }

    const row = result.rows[0];
    res.json({
      success: true,
      community: {
        id: row.id,
        name: row.name,
        displayName: row.display_name || row.name,
        description: row.description,
        logoUrl: row.config?.logo_url || null,
        bannerUrl: row.config?.banner_url || null,
        platform: row.platform,
        memberCount: row.member_count || 0,
        joinMode: row.join_mode || 'open',
        createdAt: row.created_at?.toISOString(),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get live Twitch streams
 */
export async function getLiveStreams(req, res, next) {
  try {
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '20', 10)));

    const result = await query(`
      SELECT c.entity_id, c.channel_id, c.server_id, c.viewer_count, c.live_since,
             c.stream_title, c.game_name, c.thumbnail_url
      FROM coordination c
      WHERE c.is_live = true AND c.platform = $1
      ORDER BY c.viewer_count DESC
      LIMIT $2
    `, ['twitch', limit]);

    const streams = result.rows.map(row => ({
      entityId: row.entity_id,
      channelName: row.channel_id || row.server_id,
      viewerCount: row.viewer_count || 0,
      liveSince: row.live_since?.toISOString(),
      title: row.stream_title || '',
      game: row.game_name || '',
      thumbnailUrl: row.thumbnail_url || '',
    }));

    res.json({
      success: true,
      streams,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get single stream details
 */
export async function getStreamDetails(req, res, next) {
  try {
    const { entityId } = req.params;

    const result = await query(`
      SELECT entity_id, platform, channel_id, server_id, is_live, viewer_count,
             live_since, last_updated, stream_title, game_name, thumbnail_url
      FROM coordination
      WHERE entity_id = $1
    `, [entityId]);

    if (result.rows.length === 0) {
      return next(errors.notFound('Stream not found'));
    }

    const row = result.rows[0];
    res.json({
      success: true,
      stream: {
        entityId: row.entity_id,
        platform: row.platform,
        channelName: row.channel_id || row.server_id,
        isLive: row.is_live,
        viewerCount: row.viewer_count || 0,
        liveSince: row.live_since?.toISOString(),
        lastActivity: row.last_updated?.toISOString(),
        title: row.stream_title || '',
        game: row.game_name || '',
        thumbnailUrl: row.thumbnail_url || '',
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get signup settings (public endpoint for login page)
 */
export async function getSignupSettings(req, res, next) {
  try {
    const result = await query(
      `SELECT setting_key, setting_value FROM hub_settings
       WHERE setting_key IN ('signup_enabled', 'email_configured', 'signup_allowed_domains')`
    );

    // Build settings object with defaults
    const settings = {
      signup_enabled: 'true',
      email_configured: 'false',
      signup_allowed_domains: '',
    };

    // Override with database values if they exist
    for (const row of result.rows) {
      settings[row.setting_key] = row.setting_value;
    }

    // Signup is only available if email is configured and signup is enabled
    const signupEnabled = settings.signup_enabled === 'true' && settings.email_configured === 'true';
    const allowedDomains = settings.signup_allowed_domains
      ? settings.signup_allowed_domains.split(',').map(d => d.trim()).filter(Boolean)
      : [];

    res.json({
      success: true,
      signupEnabled,
      hasAllowedDomains: allowedDomains.length > 0,
      allowedDomains: allowedDomains.length > 0 ? allowedDomains : null,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Browse marketplace modules (public endpoint)
 * GET /api/v1/marketplace/modules
 */
export async function getMarketplaceModules(req, res, next) {
  try {
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;
    const search = req.query.search || '';
    const category = req.query.category;

    let whereClause = 'WHERE is_published = true';
    const params = [];
    let paramIndex = 1;

    if (search) {
      whereClause += ` AND (name ILIKE $${paramIndex} OR display_name ILIKE $${paramIndex} OR description ILIKE $${paramIndex})`;
      params.push(`%${search}%`);
      paramIndex++;
    }

    if (category) {
      whereClause += ` AND category = $${paramIndex}`;
      params.push(category);
      paramIndex++;
    }

    // Get total count
    const countResult = await query(
      `SELECT COUNT(*) as count FROM hub_modules ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    // Get modules with aggregate stats
    const modulesResult = await query(
      `SELECT
        m.id, m.name, m.display_name, m.description, m.version,
        m.author, m.category, m.icon_url, m.is_core, m.created_at,
        COALESCE(AVG(r.rating), 0) as avg_rating,
        COUNT(DISTINCT r.id) as review_count,
        COUNT(DISTINCT inst.id) as install_count
       FROM hub_modules m
       LEFT JOIN hub_module_reviews r ON r.module_id = m.id
       LEFT JOIN hub_module_installations inst ON inst.module_id = m.id
       ${whereClause}
       GROUP BY m.id
       ORDER BY m.is_core DESC, m.created_at DESC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const modules = modulesResult.rows.map(row => ({
      id: row.id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      version: row.version,
      author: row.author,
      category: row.category,
      iconUrl: row.icon_url,
      isCore: row.is_core,
      avgRating: parseFloat(row.avg_rating || 0).toFixed(1),
      reviewCount: parseInt(row.review_count || 0, 10),
      installCount: parseInt(row.install_count || 0, 10),
      createdAt: row.created_at?.toISOString(),
    }));

    res.json({
      success: true,
      modules,
      pagination: { page, limit, total, totalPages: Math.ceil(total / limit) },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get marketplace module details (public endpoint)
 * GET /api/v1/marketplace/modules/:id
 */
export async function getMarketplaceModule(req, res, next) {
  try {
    const moduleId = parseInt(req.params.id, 10);

    if (isNaN(moduleId)) {
      return next(errors.badRequest('Invalid module ID'));
    }

    const moduleResult = await query(
      `SELECT
        m.id, m.name, m.display_name, m.description, m.version,
        m.author, m.category, m.icon_url, m.is_core, m.config_schema, m.created_at,
        COALESCE(AVG(r.rating), 0) as avg_rating,
        COUNT(DISTINCT r.id) as review_count,
        COUNT(DISTINCT inst.id) as install_count
       FROM hub_modules m
       LEFT JOIN hub_module_reviews r ON r.module_id = m.id
       LEFT JOIN hub_module_installations inst ON inst.module_id = m.id
       WHERE m.id = $1 AND m.is_published = true
       GROUP BY m.id`,
      [moduleId]
    );

    if (moduleResult.rows.length === 0) {
      return next(errors.notFound('Module not found'));
    }

    const row = moduleResult.rows[0];

    // Get recent reviews
    const reviewsResult = await query(
      `SELECT r.id, r.rating, r.review_text, r.created_at,
              u.display_name, u.avatar_url
       FROM hub_module_reviews r
       LEFT JOIN hub_users u ON u.id = r.user_id
       WHERE r.module_id = $1
       ORDER BY r.created_at DESC
       LIMIT 10`,
      [moduleId]
    );

    const module = {
      id: row.id,
      name: row.name,
      displayName: row.display_name || row.name,
      description: row.description,
      version: row.version,
      author: row.author,
      category: row.category,
      iconUrl: row.icon_url,
      isCore: row.is_core,
      configSchema: row.config_schema,
      avgRating: parseFloat(row.avg_rating || 0).toFixed(1),
      reviewCount: parseInt(row.review_count || 0, 10),
      installCount: parseInt(row.install_count || 0, 10),
      createdAt: row.created_at?.toISOString(),
      reviews: reviewsResult.rows.map(r => ({
        id: r.id,
        rating: r.rating,
        reviewText: r.review_text,
        author: r.display_name || 'Anonymous',
        authorAvatar: r.avatar_url,
        createdAt: r.created_at?.toISOString(),
      })),
    };

    res.json({ success: true, module });
  } catch (err) {
    next(err);
  }
}

/**
 * Get marketplace categories (public endpoint)
 * GET /api/v1/marketplace/categories
 */
export async function getMarketplaceCategories(req, res, next) {
  try {
    const result = await query(`
      SELECT category, COUNT(*) as module_count
      FROM hub_modules
      WHERE is_published = true AND category IS NOT NULL
      GROUP BY category
      ORDER BY module_count DESC, category ASC
    `);

    const categories = result.rows.map(row => ({
      name: row.category,
      moduleCount: parseInt(row.module_count || 0, 10),
    }));

    res.json({
      success: true,
      categories,
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get global announcement banner settings (public, no auth required)
 */
export async function getBanner(req, res, next) {
  try {
    const result = await query(
      `SELECT setting_key, setting_value FROM hub_settings
       WHERE setting_key IN ('banner_enabled', 'banner_text', 'banner_bg_color', 'banner_text_color')`
    );
    const map = Object.fromEntries(result.rows.map(r => [r.setting_key, r.setting_value]));
    res.json({
      enabled: map.banner_enabled === 'true',
      text: map.banner_text || '',
      bgColor: map.banner_bg_color || '#F5C518',
      textColor: map.banner_text_color || '#000000',
    });
  } catch (err) {
    next(err);
  }
}
