/**
 * Loyalty Controller - Proxy requests to loyalty interaction module
 * All loyalty module admin endpoints for currency, giveaways, games, and gear
 */
import { config } from '../config/index.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';

// Get loyalty module URL from environment
const LOYALTY_API_URL = process.env.LOYALTY_API_URL || 'http://loyalty-interaction:8032';

// Default config returned when loyalty service is unavailable
const DEFAULT_LOYALTY_CONFIG = {
  currency_name: 'Points',
  currency_symbol: '$',
  currency_emoji: '\uD83E\uDE99',
  chat_enabled: false,
  chat_rate: 0.5,
  chat_cooldown: 30,
  follow_enabled: false,
  follow_rate: 100,
  subscription_enabled: false,
  subscription_rate: 500,
  subscription_t2_multiplier: 2.0,
  subscription_t3_multiplier: 3.0,
  gift_subscription_enabled: false,
  gift_rate: 300,
  raid_enabled: false,
  raid_rate: 200,
  cheer_enabled: false,
  cheer_per_100bits: 100,
  donation_enabled: false,
  donation_per_dollar: 100,
  gambling_enabled: false,
  min_bet: 10,
  max_bet: 10000,
  slots_enabled: false,
  coinflip_enabled: false,
  roulette_enabled: false,
  duels_enabled: false,
  min_wager: 10,
  max_wager: 5000,
  duel_timeout: 5,
  gear_enabled: false,
  gear_drops_enabled: false,
};

/**
 * Helper function to proxy requests to loyalty module
 */
async function proxyToLoyalty(path, options = {}) {
  try {
    const url = `${LOYALTY_API_URL}${path}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': config.serviceApiKey,
        ...options.headers,
      },
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || data.message || 'Loyalty module request failed');
    }

    return data;
  } catch (err) {
    // Connection refused = loyalty module not deployed (e.g. in beta)
    if (err.cause?.code === 'ECONNREFUSED' || err.message?.includes('fetch failed')) {
      return { success: true, unavailable: true, message: 'Loyalty module not available' };
    }
    logger.error('Loyalty module proxy error', {
      path,
      error: err.message,
    });
    throw err;
  }
}

/**
 * Proxy a GET request, returning defaults when loyalty module is unavailable.
 * Merges the defaults into the unavailable response so the frontend
 * always receives the expected data shape.
 */
async function proxyGetOrDefault(path, defaults = {}) {
  const data = await proxyToLoyalty(path, { method: 'GET' });
  if (data.unavailable) {
    return { success: true, unavailable: true, ...defaults };
  }
  return data;
}

// ===== Currency Configuration =====

/**
 * Get loyalty currency configuration for community
 * GET /api/v1/admin/:communityId/loyalty/config
 */
export async function getConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/config`,
      { config: DEFAULT_LOYALTY_CONFIG }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Update loyalty currency configuration
 * PUT /api/v1/admin/:communityId/loyalty/config
 */
export async function updateConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const data = await proxyToLoyalty(`/api/v1/admin/${communityId}/loyalty/config`, {
      method: 'PUT',
      body: JSON.stringify(req.body),
    });

    logger.audit('Loyalty config updated', {
      adminId: req.user.id,
      communityId,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

// ===== Currency Management =====

/**
 * Get loyalty leaderboard
 * GET /api/v1/admin/:communityId/loyalty/leaderboard
 */
export async function getLeaderboard(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const queryParams = new URLSearchParams({
      limit: req.query.limit || '25',
      offset: req.query.offset || '0',
    });
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/leaderboard?${queryParams}`,
      { users: [], pagination: { total: 0, page: 1, limit: 25 } }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Adjust user loyalty balance
 * PUT /api/v1/admin/:communityId/loyalty/user/:userId/balance
 */
export async function adjustUserBalance(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const userId = parseInt(req.params.userId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/user/${userId}/balance`,
      {
        method: 'PUT',
        body: JSON.stringify(req.body),
      }
    );

    logger.audit('Loyalty balance adjusted', {
      adminId: req.user.id,
      communityId,
      targetUserId: userId,
      adjustment: req.body.amount || req.body.setTo,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Wipe all currency for community
 * POST /api/v1/admin/:communityId/loyalty/wipe
 */
export async function wipeAllCurrency(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const data = await proxyToLoyalty(`/api/v1/admin/${communityId}/loyalty/wipe`, {
      method: 'POST',
      body: JSON.stringify(req.body),
    });

    logger.audit('Loyalty currency wiped', {
      adminId: req.user.id,
      communityId,
      confirmation: req.body.confirmation,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Get loyalty statistics
 * GET /api/v1/admin/:communityId/loyalty/stats
 */
export async function getStats(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/stats`,
      { stats: { total_users: 0, total_currency: 0, average_balance: 0 } }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

// ===== Giveaways =====

/**
 * Get giveaways for community
 * GET /api/v1/admin/:communityId/loyalty/giveaways
 */
export async function getGiveaways(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const queryParams = new URLSearchParams();

    if (req.query.status) queryParams.set('status', req.query.status);
    if (req.query.limit) queryParams.set('limit', req.query.limit);
    if (req.query.offset) queryParams.set('offset', req.query.offset);

    const queryString = queryParams.toString();
    const path = `/api/v1/admin/${communityId}/loyalty/giveaways${queryString ? `?${queryString}` : ''}`;

    const data = await proxyGetOrDefault(path, { giveaways: [] });
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Create a new giveaway
 * POST /api/v1/admin/:communityId/loyalty/giveaways
 */
export async function createGiveaway(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const data = await proxyToLoyalty(`/api/v1/admin/${communityId}/loyalty/giveaways`, {
      method: 'POST',
      body: JSON.stringify(req.body),
    });

    logger.audit('Giveaway created', {
      adminId: req.user.id,
      communityId,
      giveawayTitle: req.body.title,
    });

    res.status(201).json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Get giveaway entries
 * GET /api/v1/admin/:communityId/loyalty/giveaways/:giveawayId/entries
 */
export async function getGiveawayEntries(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const giveawayId = parseInt(req.params.giveawayId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/giveaways/${giveawayId}/entries`,
      { entries: [] }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Draw giveaway winner
 * POST /api/v1/admin/:communityId/loyalty/giveaways/:giveawayId/draw
 */
export async function drawGiveawayWinner(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const giveawayId = parseInt(req.params.giveawayId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/giveaways/${giveawayId}/draw`,
      {
        method: 'POST',
        body: JSON.stringify(req.body),
      }
    );

    logger.audit('Giveaway winner drawn', {
      adminId: req.user.id,
      communityId,
      giveawayId,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * End a giveaway
 * PUT /api/v1/admin/:communityId/loyalty/giveaways/:giveawayId/end
 */
export async function endGiveaway(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const giveawayId = parseInt(req.params.giveawayId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/giveaways/${giveawayId}/end`,
      {
        method: 'PUT',
        body: JSON.stringify(req.body),
      }
    );

    logger.audit('Giveaway ended', {
      adminId: req.user.id,
      communityId,
      giveawayId,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

// ===== Games =====

/**
 * Get games configuration
 * GET /api/v1/admin/:communityId/loyalty/games/config
 */
export async function getGamesConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/games/config`,
      { config: { slots_enabled: false, coinflip_enabled: false, roulette_enabled: false, min_bet: 10, max_bet: 10000 } }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Update games configuration
 * PUT /api/v1/admin/:communityId/loyalty/games/config
 */
export async function updateGamesConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/games/config`,
      {
        method: 'PUT',
        body: JSON.stringify(req.body),
      }
    );

    logger.audit('Games config updated', {
      adminId: req.user.id,
      communityId,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Get games statistics
 * GET /api/v1/admin/:communityId/loyalty/games/stats
 */
export async function getGamesStats(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/games/stats`,
      { stats: { total_games: 0, total_wagered: 0, total_payouts: 0 } }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Get recent game sessions
 * GET /api/v1/admin/:communityId/loyalty/games/recent
 */
export async function getRecentGames(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const queryParams = new URLSearchParams({
      limit: req.query.limit || '25',
      offset: req.query.offset || '0',
    });

    if (req.query.gameType) {
      queryParams.set('gameType', req.query.gameType);
    }

    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/games/recent?${queryParams}`,
      { games: [] }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

// ===== Gear Shop =====

/**
 * Get gear categories
 * GET /api/v1/admin/:communityId/loyalty/gear/categories
 */
export async function getGearCategories(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/gear/categories`,
      { categories: [] }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Get gear items
 * GET /api/v1/admin/:communityId/loyalty/gear/items
 */
export async function getGearItems(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const queryParams = new URLSearchParams();

    if (req.query.category) queryParams.set('category', req.query.category);
    if (req.query.isActive !== undefined) queryParams.set('isActive', req.query.isActive);
    if (req.query.limit) queryParams.set('limit', req.query.limit);
    if (req.query.offset) queryParams.set('offset', req.query.offset);

    const queryString = queryParams.toString();
    const path = `/api/v1/admin/${communityId}/loyalty/gear/items${queryString ? `?${queryString}` : ''}`;

    const data = await proxyGetOrDefault(path, { items: [] });
    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Create gear item
 * POST /api/v1/admin/:communityId/loyalty/gear/items
 */
export async function createGearItem(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/gear/items`,
      {
        method: 'POST',
        body: JSON.stringify(req.body),
      }
    );

    logger.audit('Gear item created', {
      adminId: req.user.id,
      communityId,
      itemName: req.body.name,
    });

    res.status(201).json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Update gear item
 * PUT /api/v1/admin/:communityId/loyalty/gear/items/:itemId
 */
export async function updateGearItem(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const itemId = parseInt(req.params.itemId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/gear/items/${itemId}`,
      {
        method: 'PUT',
        body: JSON.stringify(req.body),
      }
    );

    logger.audit('Gear item updated', {
      adminId: req.user.id,
      communityId,
      itemId,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Delete gear item
 * DELETE /api/v1/admin/:communityId/loyalty/gear/items/:itemId
 */
export async function deleteGearItem(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const itemId = parseInt(req.params.itemId, 10);

    const data = await proxyToLoyalty(
      `/api/v1/admin/${communityId}/loyalty/gear/items/${itemId}`,
      { method: 'DELETE' }
    );

    logger.audit('Gear item deleted', {
      adminId: req.user.id,
      communityId,
      itemId,
    });

    res.json(data);
  } catch (err) {
    next(err);
  }
}

/**
 * Get gear shop statistics
 * GET /api/v1/admin/:communityId/loyalty/gear/stats
 */
export async function getGearStats(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const data = await proxyGetOrDefault(
      `/api/v1/admin/${communityId}/loyalty/gear/stats`,
      { stats: { total_items: 0, total_sold: 0, total_revenue: 0 } }
    );
    res.json(data);
  } catch (err) {
    next(err);
  }
}
