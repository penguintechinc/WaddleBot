/**
 * AI Chatter Controller
 * Proxies AIChatter configuration to ai_interaction_module.
 * Only community admins can configure AIChatter for their community.
 */
import axios from 'axios';
import { config } from '../config/index.js';
import { logger } from '../utils/logger.js';
import { errors } from '../middleware/errorHandler.js';

function getAiInteractionClient() {
  const baseURL = process.env.AI_INTERACTION_API_URL || 'http://ai-interaction:8005';
  return axios.create({
    baseURL,
    timeout: 8000,
    headers: { 'X-Service-Key': config.serviceApiKey },
  });
}

/**
 * GET /api/v1/admin/:communityId/ai-chatter/config
 */
export async function getChatterConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const client = getAiInteractionClient();
    const response = await client.get('/api/v1/ai/config/chatter', {
      params: { community_id: communityId },
    });
    res.json({ success: true, config: response.data?.data || response.data });
  } catch (err) {
    if (err.response?.status === 404) {
      // No config yet — return defaults
      return res.json({
        success: true,
        config: {
          enabled: false,
          max_responses_per_window: 10,
          window_seconds: 600,
          max_per_user_per_window: 2,
          response_probability: 0.30,
          min_message_length: 10,
        },
      });
    }
    logger.error('Failed to fetch AIChatter config', { communityId: req.params.communityId, error: err.message });
    next(err);
  }
}

/**
 * PUT /api/v1/admin/:communityId/ai-chatter/config
 */
export async function updateChatterConfig(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const { enabled, max_responses_per_window, window_seconds, max_per_user_per_window, response_probability, min_message_length } = req.body;

    // Validate
    if (max_responses_per_window !== undefined) {
      const v = parseInt(max_responses_per_window, 10);
      if (isNaN(v) || v < 1 || v > 100) {
        return next(errors.badRequest('max_responses_per_window must be 1-100'));
      }
    }
    if (window_seconds !== undefined) {
      const v = parseInt(window_seconds, 10);
      if (isNaN(v) || v < 60 || v > 3600) {
        return next(errors.badRequest('window_seconds must be 60-3600'));
      }
    }
    if (max_per_user_per_window !== undefined) {
      const v = parseInt(max_per_user_per_window, 10);
      if (isNaN(v) || v < 1 || v > 20) {
        return next(errors.badRequest('max_per_user_per_window must be 1-20'));
      }
    }
    if (response_probability !== undefined) {
      const v = parseFloat(response_probability);
      if (isNaN(v) || v < 0.05 || v > 1.0) {
        return next(errors.badRequest('response_probability must be 0.05-1.0'));
      }
    }

    const client = getAiInteractionClient();
    const response = await client.post('/api/v1/ai/config/chatter', {
      community_id: communityId,
      ...(enabled !== undefined && { enabled: Boolean(enabled) }),
      ...(max_responses_per_window !== undefined && { max_responses_per_window: parseInt(max_responses_per_window, 10) }),
      ...(window_seconds !== undefined && { window_seconds: parseInt(window_seconds, 10) }),
      ...(max_per_user_per_window !== undefined && { max_per_user_per_window: parseInt(max_per_user_per_window, 10) }),
      ...(response_probability !== undefined && { response_probability: parseFloat(response_probability) }),
      ...(min_message_length !== undefined && { min_message_length: parseInt(min_message_length, 10) }),
    });

    logger.audit('AIChatter config updated', {
      community: String(communityId),
      user: req.user.userId,
      action: 'update_ai_chatter_config',
      result: 'success',
    });

    res.json({ success: true, config: response.data?.data || response.data });
  } catch (err) {
    logger.error('Failed to update AIChatter config', { communityId: req.params.communityId, error: err.message });
    next(err);
  }
}
