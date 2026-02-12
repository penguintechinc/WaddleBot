/**
 * Platform Configuration Controller
 * Manages bot credentials and OAuth integrations via platform_integrations table
 */

import { query } from '../config/database.js';
import { logger } from '../utils/logger.js';

class PlatformConfigController {
  /**
   * Get all platform configurations by type
   */
  static async getPlatformConfigs(req, res) {
    try {
      const { integrationType, platform } = req.query;

      let sql = 'SELECT * FROM platform_integrations WHERE is_active = TRUE';
      const params = [];

      if (integrationType) {
        sql += ' AND integration_type = $' + (params.length + 1);
        params.push(integrationType);
      }

      if (platform) {
        sql += ' AND platform = $' + (params.length + 1);
        params.push(platform);
      }

      sql += ' ORDER BY platform, integration_type, created_at DESC';

      const result = await query(sql, params);

      return res.json({
        success: true,
        data: result.rows.map(row => formatCredential(row)),
        count: result.rows.length,
      });
    } catch (error) {
      logger.error('Error fetching platform configs:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to fetch platform configurations',
      });
    }
  }

  /**
   * Get bot credentials for a specific platform
   */
  static async getBotCredentials(req, res) {
    try {
      const { platform } = req.params;

      const result = await query(
        `SELECT * FROM platform_integrations
         WHERE platform = $1
         AND integration_type = 'bot'
         AND is_active = TRUE
         LIMIT 1`,
        [platform]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          success: false,
          error: `No bot credentials found for platform: ${platform}`,
        });
      }

      const credential = formatCredential(result.rows[0]);
      return res.json({
        success: true,
        data: credential,
      });
    } catch (error) {
      logger.error('Error fetching bot credentials:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to fetch bot credentials',
      });
    }
  }

  /**
   * Get community OAuth tokens
   */
  static async getCommunityCredentials(req, res) {
    try {
      const { communityId } = req.params;

      const result = await query(
        `SELECT * FROM platform_integrations
         WHERE community_id = $1
         AND integration_type = 'community_oauth'
         AND is_active = TRUE
         ORDER BY platform`,
        [communityId]
      );

      return res.json({
        success: true,
        data: result.rows.map(row => formatCredential(row)),
        count: result.rows.length,
      });
    } catch (error) {
      logger.error('Error fetching community credentials:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to fetch community credentials',
      });
    }
  }

  /**
   * Get user OAuth tokens
   */
  static async getUserCredentials(req, res) {
    try {
      const { userId } = req.params;

      const result = await query(
        `SELECT * FROM platform_integrations
         WHERE user_id = $1
         AND integration_type = 'user_oauth'
         AND is_active = TRUE
         ORDER BY platform`,
        [userId]
      );

      return res.json({
        success: true,
        data: result.rows.map(row => formatCredential(row)),
        count: result.rows.length,
      });
    } catch (error) {
      logger.error('Error fetching user credentials:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to fetch user credentials',
      });
    }
  }

  /**
   * Create new platform credential
   */
  static async createPlatformConfig(req, res) {
    try {
      const {
        platform,
        integrationType,
        communityId,
        userId,
        accessToken,
        refreshToken,
        clientId,
        clientSecret,
        expiresAt,
        scopes,
        configData,
      } = req.body;

      // Validate required fields
      if (!platform || !integrationType) {
        return res.status(400).json({
          success: false,
          error: 'platform and integrationType are required',
        });
      }

      // Validate scope constraints
      const scopeError = validateScopeConstraints(integrationType, communityId, userId);
      if (scopeError) {
        return res.status(400).json({
          success: false,
          error: scopeError,
        });
      }

      const result = await query(
        `INSERT INTO platform_integrations (
          platform, integration_type, community_id, user_id,
          access_token, refresh_token, client_id, client_secret,
          token_type, expires_at, scopes, config_data,
          is_active, is_encrypted, created_at, updated_at,
          created_by_user_id, updated_by_user_id
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, NOW(), NOW(), $15, $16)
        RETURNING *`,
        [
          platform,
          integrationType,
          communityId || null,
          userId || null,
          accessToken || null,
          refreshToken || null,
          clientId || null,
          clientSecret || null,
          'Bearer',
          expiresAt || null,
          scopes || [],
          JSON.stringify(configData || {}),
          true,
          true,
          req.user?.id || null,
          req.user?.id || null,
        ]
      );

      logger.info(`Created platform credential: ${platform}/${integrationType}`);

      return res.status(201).json({
        success: true,
        data: formatCredential(result.rows[0]),
      });
    } catch (error) {
      logger.error('Error creating platform config:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to create platform configuration',
      });
    }
  }

  /**
   * Update existing platform credential
   */
  static async updatePlatformConfig(req, res) {
    try {
      const { id } = req.params;
      const {
        accessToken,
        refreshToken,
        clientId,
        clientSecret,
        expiresAt,
        scopes,
        configData,
        isActive,
      } = req.body;

      const result = await query(
        `UPDATE platform_integrations
         SET access_token = COALESCE($2, access_token),
             refresh_token = COALESCE($3, refresh_token),
             client_id = COALESCE($4, client_id),
             client_secret = COALESCE($5, client_secret),
             expires_at = COALESCE($6, expires_at),
             scopes = COALESCE($7, scopes),
             config_data = COALESCE($8, config_data),
             is_active = COALESCE($9, is_active),
             updated_at = NOW(),
             updated_by_user_id = $10
         WHERE id = $1
         RETURNING *`,
        [
          id,
          accessToken || null,
          refreshToken || null,
          clientId || null,
          clientSecret || null,
          expiresAt || null,
          scopes || null,
          configData ? JSON.stringify(configData) : null,
          isActive !== undefined ? isActive : null,
          req.user?.id || null,
        ]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          success: false,
          error: 'Credential not found',
        });
      }

      logger.info(`Updated platform credential: ${id}`);

      return res.json({
        success: true,
        data: formatCredential(result.rows[0]),
      });
    } catch (error) {
      logger.error('Error updating platform config:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to update platform configuration',
      });
    }
  }

  /**
   * Delete (deactivate) platform credential
   */
  static async deletePlatformConfig(req, res) {
    try {
      const { id } = req.params;

      const result = await query(
        `UPDATE platform_integrations
         SET is_active = FALSE, updated_at = NOW(), updated_by_user_id = $2
         WHERE id = $1
         RETURNING *`,
        [id, req.user?.id || null]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          success: false,
          error: 'Credential not found',
        });
      }

      logger.info(`Deactivated platform credential: ${id}`);

      return res.json({
        success: true,
        message: 'Credential deactivated successfully',
      });
    } catch (error) {
      logger.error('Error deleting platform config:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to delete platform configuration',
      });
    }
  }

  /**
   * Test credential with platform API
   */
  static async testCredential(req, res) {
    try {
      const { id } = req.params;

      const result = await query(
        'SELECT * FROM platform_integrations WHERE id = $1',
        [id]
      );

      if (result.rows.length === 0) {
        return res.status(404).json({
          success: false,
          error: 'Credential not found',
        });
      }

      const credential = result.rows[0];

      // Test based on platform
      const testResult = await testPlatformCredential(credential);

      if (!testResult.valid) {
        return res.status(400).json({
          success: false,
          error: `Credential validation failed: ${testResult.error}`,
        });
      }

      logger.info(`Tested credential: ${id} (${credential.platform})`);

      return res.json({
        success: true,
        message: 'Credential is valid',
        data: {
          platform: credential.platform,
          valid: true,
          testedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      logger.error('Error testing credential:', error);
      return res.status(500).json({
        success: false,
        error: 'Failed to test credential',
      });
    }
  }
}

/**
 * Helper: Format credential for API response (mask sensitive fields)
 */
function formatCredential(row) {
  return {
    id: row.id,
    platform: row.platform,
    integrationType: row.integration_type,
    communityId: row.community_id,
    userId: row.user_id,
    accessToken: row.access_token ? '***' : null,
    refreshToken: row.refresh_token ? '***' : null,
    clientId: row.client_id,
    clientSecret: row.client_secret ? '***' : null,
    tokenType: row.token_type,
    expiresAt: row.expires_at,
    scopes: row.scopes,
    configData: row.config_data,
    isActive: row.is_active,
    isEncrypted: row.is_encrypted,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    createdByUserId: row.created_by_user_id,
    updatedByUserId: row.updated_by_user_id,
  };
}

/**
 * Helper: Validate scope constraints
 */
function validateScopeConstraints(integrationType, communityId, userId) {
  if (integrationType === 'bot') {
    if (communityId !== undefined || userId !== undefined) {
      return 'Bot credentials cannot have community_id or user_id';
    }
  } else if (integrationType === 'community_oauth') {
    if (!communityId) {
      return 'Community OAuth requires community_id';
    }
    if (userId !== undefined) {
      return 'Community OAuth cannot have user_id';
    }
  } else if (integrationType === 'user_oauth') {
    if (!userId) {
      return 'User OAuth requires user_id';
    }
    if (communityId !== undefined) {
      return 'User OAuth cannot have community_id';
    }
  }
  return null;
}

/**
 * Helper: Test credential with platform API
 */
async function testPlatformCredential(credential) {
  const { platform, access_token } = credential;

  try {
    switch (platform) {
      case 'twitch':
        return await testTwitchToken(access_token);
      case 'discord':
        return await testDiscordToken(access_token);
      case 'slack':
        return await testSlackToken(access_token);
      case 'youtube':
        return await testYouTubeToken(access_token);
      default:
        return { valid: true };
    }
  } catch (error) {
    return { valid: false, error: error.message };
  }
}

/**
 * Helper: Test Twitch token
 */
async function testTwitchToken(token) {
  try {
    const response = await fetch('https://id.twitch.tv/oauth2/validate', {
      headers: { 'Authorization': `OAuth ${token}` },
    });
    return { valid: response.ok };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}

/**
 * Helper: Test Discord token
 */
async function testDiscordToken(token) {
  try {
    const response = await fetch('https://discord.com/api/users/@me', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    return { valid: response.ok };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}

/**
 * Helper: Test Slack token
 */
async function testSlackToken(token) {
  try {
    const response = await fetch('https://slack.com/api/auth.test', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
    });
    const data = await response.json();
    return { valid: data.ok };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}

/**
 * Helper: Test YouTube token
 */
async function testYouTubeToken(token) {
  try {
    const response = await fetch('https://www.googleapis.com/youtube/v3/channels?part=id&mine=true', {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    return { valid: response.ok };
  } catch (error) {
    return { valid: false, error: error.message };
  }
}

export default PlatformConfigController;
