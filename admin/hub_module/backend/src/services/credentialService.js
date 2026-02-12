/**
 * Credential Service
 * Handles CRUD, encryption, validation, and platform API testing for platform_integrations
 */

import { query } from '../config/database.js';
import crypto from 'crypto';
import { logger } from '../utils/logger.js';

// Encryption configuration
const ENCRYPTION_ALGORITHM = 'aes-256-cbc';
const ENCRYPTION_KEY_LENGTH = 32; // 256 bits
const IV_LENGTH = 16; // 128 bits

class CredentialService {
  /**
   * Get credential by ID
   */
  static async getCredentialById(id) {
    try {
      const result = await query(
        'SELECT * FROM platform_integrations WHERE id = $1',
        [id]
      );

      if (result.rows.length === 0) {
        throw new Error(`Credential not found: ${id}`);
      }

      return result.rows[0];
    } catch (error) {
      logger.error(`Error fetching credential ${id}:`, error);
      throw error;
    }
  }

  /**
   * Get credentials by platform
   */
  static async getCredentialsByPlatform(platform, integrationType = 'bot') {
    try {
      const result = await query(
        `SELECT * FROM platform_integrations
         WHERE platform = $1
         AND integration_type = $2
         AND is_active = TRUE
         ORDER BY created_at DESC`,
        [platform, integrationType]
      );

      return result.rows;
    } catch (error) {
      logger.error(`Error fetching credentials for ${platform}:`, error);
      throw error;
    }
  }

  /**
   * Get credentials by community
   */
  static async getCredentialsByCommunity(communityId) {
    try {
      const result = await query(
        `SELECT * FROM platform_integrations
         WHERE community_id = $1
         AND integration_type = 'community_oauth'
         AND is_active = TRUE
         ORDER BY platform`,
        [communityId]
      );

      return result.rows;
    } catch (error) {
      logger.error(`Error fetching community credentials for ${communityId}:`, error);
      throw error;
    }
  }

  /**
   * Get credentials by user
   */
  static async getCredentialsByUser(userId) {
    try {
      const result = await query(
        `SELECT * FROM platform_integrations
         WHERE user_id = $1
         AND integration_type = 'user_oauth'
         AND is_active = TRUE
         ORDER BY platform`,
        [userId]
      );

      return result.rows;
    } catch (error) {
      logger.error(`Error fetching user credentials for ${userId}:`, error);
      throw error;
    }
  }

  /**
   * Create credential
   */
  static async createCredential(data, userId) {
    try {
      const {
        platform,
        integrationType,
        communityId,
        userId: credentialUserId,
        accessToken,
        refreshToken,
        clientId,
        clientSecret,
        expiresAt,
        scopes,
        configData,
      } = data;

      // Validate required fields
      this.validateCredentialData(platform, data);

      // Validate scope constraints
      this.validateScopeConstraints(integrationType, communityId, credentialUserId);

      // Encrypt sensitive fields if present
      const encryptedAccessToken = accessToken
        ? this.encryptCredential(accessToken)
        : null;
      const encryptedRefreshToken = refreshToken
        ? this.encryptCredential(refreshToken)
        : null;
      const encryptedClientSecret = clientSecret
        ? this.encryptCredential(clientSecret)
        : null;

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
          credentialUserId || null,
          encryptedAccessToken || null,
          encryptedRefreshToken || null,
          clientId || null,
          encryptedClientSecret || null,
          'Bearer',
          expiresAt || null,
          scopes || [],
          JSON.stringify(configData || {}),
          true,
          true,
          userId,
          userId,
        ]
      );

      logger.info(`Created credential: ${platform}/${integrationType} by user ${userId}`);
      return result.rows[0];
    } catch (error) {
      logger.error('Error creating credential:', error);
      throw error;
    }
  }

  /**
   * Update credential
   */
  static async updateCredential(id, data, userId) {
    try {
      const credential = await this.getCredentialById(id);

      if (!credential) {
        throw new Error(`Credential not found: ${id}`);
      }

      const {
        accessToken,
        refreshToken,
        clientId,
        clientSecret,
        expiresAt,
        scopes,
        configData,
        isActive,
      } = data;

      // Encrypt sensitive fields if provided
      const updates = {};
      if (accessToken !== undefined) {
        updates.access_token = accessToken ? this.encryptCredential(accessToken) : null;
      }
      if (refreshToken !== undefined) {
        updates.refresh_token = refreshToken ? this.encryptCredential(refreshToken) : null;
      }
      if (clientId !== undefined) {
        updates.client_id = clientId || null;
      }
      if (clientSecret !== undefined) {
        updates.client_secret = clientSecret ? this.encryptCredential(clientSecret) : null;
      }
      if (expiresAt !== undefined) {
        updates.expires_at = expiresAt || null;
      }
      if (scopes !== undefined) {
        updates.scopes = scopes || [];
      }
      if (configData !== undefined) {
        updates.config_data = JSON.stringify(configData || {});
      }
      if (isActive !== undefined) {
        updates.is_active = isActive;
      }

      // Build dynamic query
      const setClause = Object.keys(updates)
        .map((key, idx) => `${key} = $${idx + 2}`)
        .join(', ');

      const values = [id, ...Object.values(updates), userId];

      const result = await query(
        `UPDATE platform_integrations
         SET ${setClause}, updated_at = NOW(), updated_by_user_id = $${values.length}
         WHERE id = $1
         RETURNING *`,
        values
      );

      logger.info(`Updated credential: ${id} by user ${userId}`);
      return result.rows[0];
    } catch (error) {
      logger.error(`Error updating credential ${id}:`, error);
      throw error;
    }
  }

  /**
   * Delete (deactivate) credential
   */
  static async deleteCredential(id, userId) {
    try {
      const result = await query(
        `UPDATE platform_integrations
         SET is_active = FALSE, updated_at = NOW(), updated_by_user_id = $2
         WHERE id = $1
         RETURNING *`,
        [id, userId]
      );

      if (result.rows.length === 0) {
        throw new Error(`Credential not found: ${id}`);
      }

      logger.info(`Deactivated credential: ${id} by user ${userId}`);
      return result.rows[0];
    } catch (error) {
      logger.error(`Error deleting credential ${id}:`, error);
      throw error;
    }
  }

  /**
   * Encrypt credential (AES-256-CBC)
   */
  static encryptCredential(plaintext) {
    try {
      // Generate random IV
      const iv = crypto.randomBytes(IV_LENGTH);

      // Get encryption key from environment or use default
      const key = crypto
        .createHash('sha256')
        .update(process.env.ENCRYPTION_KEY || 'default-insecure-key')
        .digest();

      // Create cipher
      const cipher = crypto.createCipheriv(ENCRYPTION_ALGORITHM, key, iv);

      // Encrypt
      let encrypted = cipher.update(plaintext, 'utf8', 'hex');
      encrypted += cipher.final('hex');

      // Return IV + encrypted data (IV needed for decryption)
      return `${iv.toString('hex')}:${encrypted}`;
    } catch (error) {
      logger.error('Error encrypting credential:', error);
      throw new Error('Encryption failed');
    }
  }

  /**
   * Decrypt credential
   */
  static decryptCredential(encryptedData) {
    try {
      // Split IV and encrypted data
      const [ivHex, encrypted] = encryptedData.split(':');
      const iv = Buffer.from(ivHex, 'hex');

      // Get encryption key
      const key = crypto
        .createHash('sha256')
        .update(process.env.ENCRYPTION_KEY || 'default-insecure-key')
        .digest();

      // Create decipher
      const decipher = crypto.createDecipheriv(ENCRYPTION_ALGORITHM, key, iv);

      // Decrypt
      let decrypted = decipher.update(encrypted, 'hex', 'utf8');
      decrypted += decipher.final('utf8');

      return decrypted;
    } catch (error) {
      logger.error('Error decrypting credential:', error);
      throw new Error('Decryption failed');
    }
  }

  /**
   * Validate credential data
   */
  static validateCredentialData(platform, data) {
    if (!platform) {
      throw new Error('platform is required');
    }

    if (!data.integrationType) {
      throw new Error('integrationType is required');
    }

    // Platform-specific validations
    switch (platform) {
      case 'twitch':
      case 'discord':
      case 'slack':
      case 'youtube':
      case 'spotify':
        if (!data.accessToken && !data.clientId) {
          throw new Error('accessToken or clientId is required');
        }
        break;
      default:
        // Unknown platform, minimal validation
        break;
    }
  }

  /**
   * Validate scope constraints
   */
  static validateScopeConstraints(integrationType, communityId, userId) {
    if (integrationType === 'bot') {
      if (communityId || userId) {
        throw new Error('Bot credentials cannot have community_id or user_id');
      }
    } else if (integrationType === 'community_oauth') {
      if (!communityId) {
        throw new Error('Community OAuth requires community_id');
      }
      if (userId) {
        throw new Error('Community OAuth cannot have user_id');
      }
    } else if (integrationType === 'user_oauth') {
      if (!userId) {
        throw new Error('User OAuth requires user_id');
      }
      if (communityId) {
        throw new Error('User OAuth cannot have community_id');
      }
    } else {
      throw new Error(`Unknown integration type: ${integrationType}`);
    }
  }

  /**
   * Test credential with platform API
   */
  static async testCredential(credential) {
    const { platform, access_token } = credential;

    try {
      switch (platform) {
        case 'twitch':
          return await this.testTwitchToken(access_token);
        case 'discord':
          return await this.testDiscordToken(access_token);
        case 'slack':
          return await this.testSlackToken(access_token);
        case 'youtube':
          return await this.testYouTubeToken(access_token);
        case 'spotify':
          return await this.testSpotifyToken(access_token);
        default:
          return { valid: true, message: 'Unknown platform, skipped validation' };
      }
    } catch (error) {
      logger.error(`Error testing credential for ${platform}:`, error);
      return { valid: false, error: error.message };
    }
  }

  /**
   * Test Twitch token
   */
  static async testTwitchToken(token) {
    try {
      const response = await fetch('https://id.twitch.tv/oauth2/validate', {
        headers: { 'Authorization': `OAuth ${token}` },
      });
      return { valid: response.ok, message: response.ok ? 'Token valid' : 'Token invalid' };
    } catch (error) {
      return { valid: false, error: error.message };
    }
  }

  /**
   * Test Discord token
   */
  static async testDiscordToken(token) {
    try {
      const response = await fetch('https://discord.com/api/users/@me', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      return { valid: response.ok, message: response.ok ? 'Token valid' : 'Token invalid' };
    } catch (error) {
      return { valid: false, error: error.message };
    }
  }

  /**
   * Test Slack token
   */
  static async testSlackToken(token) {
    try {
      const response = await fetch('https://slack.com/api/auth.test', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
      const data = await response.json();
      return { valid: data.ok, message: data.ok ? 'Token valid' : data.error };
    } catch (error) {
      return { valid: false, error: error.message };
    }
  }

  /**
   * Test YouTube token
   */
  static async testYouTubeToken(token) {
    try {
      const response = await fetch(
        'https://www.googleapis.com/youtube/v3/channels?part=id&mine=true',
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      return { valid: response.ok, message: response.ok ? 'Token valid' : 'Token invalid' };
    } catch (error) {
      return { valid: false, error: error.message };
    }
  }

  /**
   * Test Spotify token
   */
  static async testSpotifyToken(token) {
    try {
      const response = await fetch('https://api.spotify.com/v1/me', {
        headers: { 'Authorization': `Bearer ${token}` },
      });
      return { valid: response.ok, message: response.ok ? 'Token valid' : 'Token invalid' };
    } catch (error) {
      return { valid: false, error: error.message };
    }
  }
}

export default CredentialService;
