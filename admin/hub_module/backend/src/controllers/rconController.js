/**
 * Server Manager (RCON/Voice) Controller
 * Handles CRUD for game/voice servers, proxies commands to Python module
 */
import { query } from '../config/database.js';
import logger from '../utils/logger.js';
import { encrypt } from '../utils/encryption.js';

const SERVER_MANAGER_URL = process.env.SERVER_MANAGER_URL || 'http://server-manager-service:8098';

// SSRF protection: reject private/reserved IPs
const PRIVATE_IP_PATTERNS = [
  /^10\./,
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
  /^192\.168\./,
  /^127\./,
  /^0\./,
  /^169\.254\./,
  /^::1$/,
  /^fc00:/i,
  /^fe80:/i,
  /^localhost$/i,
];

function isPrivateHost(host) {
  return PRIVATE_IP_PATTERNS.some(pattern => pattern.test(host));
}

async function proxyToModule(path, method = 'GET', body = null) {
  const url = `${SERVER_MANAGER_URL}${path}`;
  const options = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) options.body = JSON.stringify(body);
  const resp = await fetch(url, options);
  return resp.json();
}

// ── Admin Functions ────────────────────────────────────────────

export async function listServers(req, res, next) {
  try {
    const { communityId } = req.params;
    const isAdmin = req.isCommunityAdmin;

    let result;
    if (isAdmin) {
      result = await query(
        `SELECT id, display_name, game_name, server_type, host, game_port,
                rcon_port, game_type, visibility, status_api_type, is_active,
                metadata, created_at, updated_at
         FROM server_status_configs
         WHERE community_id = $1 AND deleted_at IS NULL
         ORDER BY display_name ASC`,
        [communityId]
      );
    } else {
      // Members see filtered view — no host/port/credential details
      result = await query(
        `SELECT id, display_name, game_name, server_type, game_port,
                game_type, visibility, is_active, metadata
         FROM server_status_configs
         WHERE community_id = $1 AND deleted_at IS NULL
           AND visibility IN ('members', 'registered')
         ORDER BY display_name ASC`,
        [communityId]
      );
    }
    res.json({ servers: result.rows });
  } catch (err) {
    logger.error('Failed to list servers', { error: err.message });
    next(err);
  }
}

export async function createServer(req, res, next) {
  try {
    const { communityId } = req.params;
    const {
      display_name, game_name, server_type, host, game_port,
      rcon_port, password, game_type, visibility, status_api_type,
      status_url, metadata
    } = req.body;

    if (!display_name || !display_name.trim()) {
      return res.status(400).json({ error: 'Display name is required' });
    }
    if (!host || !host.trim()) {
      return res.status(400).json({ error: 'Host is required' });
    }
    if (isPrivateHost(host.trim())) {
      return res.status(400).json({ error: 'Private/reserved IP addresses are not allowed' });
    }

    let credentialEnc = null;
    let credentialIv = null;
    if (password) {
      const encrypted = encrypt(password);
      credentialEnc = encrypted.ciphertext;
      credentialIv = encrypted.iv;
    }

    const result = await query(
      `INSERT INTO server_status_configs
         (community_id, display_name, game_name, server_type, host, game_port,
          rcon_port, credential_enc, credential_iv, game_type, visibility,
          status_api_type, status_url, added_by, metadata, is_active)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, TRUE)
       RETURNING id, display_name, game_name, server_type, host, game_port,
                 rcon_port, game_type, visibility, status_api_type, is_active,
                 metadata, created_at`,
      [
        communityId,
        display_name.trim(),
        game_name || display_name.trim().toLowerCase().replace(/\s+/g, '_'),
        server_type || 'rcon',
        host.trim(),
        game_port || null,
        rcon_port || null,
        credentialEnc,
        credentialIv,
        game_type || 'other',
        visibility || 'admin_only',
        status_api_type || 'rcon',
        status_url || null,
        req.user.id,
        JSON.stringify(metadata || {}),
      ]
    );
    res.status(201).json({ server: result.rows[0] });
  } catch (err) {
    logger.error('Failed to create server', { error: err.message });
    next(err);
  }
}

export async function updateServer(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const {
      display_name, game_name, server_type, host, game_port,
      rcon_port, password, game_type, visibility, status_api_type,
      status_url, metadata
    } = req.body;

    if (host && isPrivateHost(host.trim())) {
      return res.status(400).json({ error: 'Private/reserved IP addresses are not allowed' });
    }

    let credentialUpdate = '';
    const params = [
      display_name ? display_name.trim() : null,
      game_name || null,
      server_type || null,
      host ? host.trim() : null,
      game_port || null,
      rcon_port || null,
      game_type || null,
      visibility || null,
      status_api_type || null,
      status_url,
      metadata ? JSON.stringify(metadata) : null,
      serverId,
      communityId,
    ];

    if (password) {
      const encrypted = encrypt(password);
      credentialUpdate = ', credential_enc = $14, credential_iv = $15';
      params.push(encrypted.ciphertext, encrypted.iv);
    }

    const result = await query(
      `UPDATE server_status_configs
       SET display_name    = COALESCE($1, display_name),
           game_name       = COALESCE($2, game_name),
           server_type     = COALESCE($3, server_type),
           host            = COALESCE($4, host),
           game_port       = COALESCE($5, game_port),
           rcon_port       = COALESCE($6, rcon_port),
           game_type       = COALESCE($7, game_type),
           visibility      = COALESCE($8, visibility),
           status_api_type = COALESCE($9, status_api_type),
           status_url      = $10,
           metadata        = COALESCE($11, metadata),
           updated_at      = NOW()
           ${credentialUpdate}
       WHERE id = $12 AND community_id = $13 AND deleted_at IS NULL
       RETURNING id, display_name, game_name, server_type, host, game_port,
                 rcon_port, game_type, visibility, status_api_type, is_active,
                 metadata, updated_at`,
      params
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Server not found' });
    }
    res.json({ server: result.rows[0] });
  } catch (err) {
    logger.error('Failed to update server', { error: err.message });
    next(err);
  }
}

export async function deleteServer(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await query(
      `UPDATE server_status_configs
       SET deleted_at = NOW()
       WHERE id = $1 AND community_id = $2 AND deleted_at IS NULL
       RETURNING id`,
      [serverId, communityId]
    );
    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Server not found' });
    }
    res.json({ message: 'Server deleted' });
  } catch (err) {
    logger.error('Failed to delete server', { error: err.message });
    next(err);
  }
}

export async function testConnection(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const server = await query(
      'SELECT server_type, host, rcon_port, credential_enc, credential_iv, metadata FROM server_status_configs WHERE id = $1 AND community_id = $2 AND deleted_at IS NULL',
      [serverId, communityId]
    );
    if (server.rows.length === 0) {
      return res.status(404).json({ error: 'Server not found' });
    }

    const s = server.rows[0];
    const body = {
      server_type: s.server_type,
      host: s.host,
      port: s.rcon_port,
    };

    // For test, we decrypt and send password to Python module
    // Password is passed in body because test_connection doesn't need stored creds
    if (req.body.password) {
      body.password = req.body.password;
    }

    if (s.server_type === 'teamspeak') {
      body.username = (s.metadata || {}).ts_username || 'serveradmin';
    }

    const result = await proxyToModule(`/api/v1/server-manager/${communityId}/connect-test`, 'POST', body);
    res.json(result);
  } catch (err) {
    logger.error('Failed to test connection', { error: err.message });
    next(err);
  }
}

export async function executeCommand(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const { command } = req.body;

    if (!command || !command.trim()) {
      return res.status(400).json({ error: 'Command is required' });
    }

    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/command`,
      'POST',
      { server_id: serverId, command: command.trim(), user_id: req.user.id }
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to execute command', { error: err.message });
    next(err);
  }
}

export async function getServerStatus(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await proxyToModule(`/api/v1/server-manager/${communityId}/servers/${serverId}/status`);
    res.json(result);
  } catch (err) {
    logger.error('Failed to get server status', { error: err.message });
    next(err);
  }
}

export async function getPlayerList(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await proxyToModule(`/api/v1/server-manager/${communityId}/servers/${serverId}/players`);
    res.json(result);
  } catch (err) {
    logger.error('Failed to get player list', { error: err.message });
    next(err);
  }
}

export async function kickPlayer(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const { player, reason } = req.body;
    if (!player) {
      return res.status(400).json({ error: 'Player identifier is required' });
    }
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/kick`,
      'POST',
      { player, reason: reason || '', user_id: req.user.id }
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to kick player', { error: err.message });
    next(err);
  }
}

export async function banPlayer(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const { player, reason, duration } = req.body;
    if (!player) {
      return res.status(400).json({ error: 'Player identifier is required' });
    }
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/ban`,
      'POST',
      { player, reason: reason || '', duration: duration || 0, user_id: req.user.id }
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to ban player', { error: err.message });
    next(err);
  }
}

export async function getChannels(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await proxyToModule(`/api/v1/server-manager/${communityId}/servers/${serverId}/channels`);
    res.json(result);
  } catch (err) {
    logger.error('Failed to get channels', { error: err.message });
    next(err);
  }
}

export async function moveUser(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const { user_id: targetUserId, channel_id } = req.body;
    if (!targetUserId || channel_id === undefined) {
      return res.status(400).json({ error: 'user_id and channel_id are required' });
    }
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/move`,
      'POST',
      { user_id: targetUserId, channel_id }
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to move user', { error: err.message });
    next(err);
  }
}

export async function sendMessage(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const { text, channel_id, target_mode } = req.body;
    if (!text || !text.trim()) {
      return res.status(400).json({ error: 'Message text is required' });
    }
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/message`,
      'POST',
      { text: text.trim(), channel_id: channel_id || 0, target_mode: target_mode || 2 }
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to send message', { error: err.message });
    next(err);
  }
}

export async function getCommandLog(req, res, next) {
  try {
    const { communityId } = req.params;
    const { limit = 50, offset = 0, server_id } = req.query;

    const conditions = [
      'ssc.community_id = $1',
      'ssc.deleted_at IS NULL',
    ];
    const params = [communityId];
    let idx = 2;

    if (server_id) {
      conditions.push(`rcl.server_config_id = $${idx++}`);
      params.push(server_id);
    }

    const where = conditions.join(' AND ');
    const result = await query(
      `SELECT rcl.id, rcl.server_config_id, rcl.command, rcl.response_summary,
              rcl.success, rcl.executed_at, rcl.user_id,
              ssc.display_name as server_name,
              hu.display_name as user_name
       FROM rcon_command_log rcl
       JOIN server_status_configs ssc ON rcl.server_config_id = ssc.id
       LEFT JOIN hub_users hu ON rcl.user_id = hu.id
       WHERE ${where}
       ORDER BY rcl.executed_at DESC
       LIMIT $${idx++} OFFSET $${idx++}`,
      [...params, parseInt(limit), parseInt(offset)]
    );
    res.json({ log: result.rows });
  } catch (err) {
    logger.error('Failed to get command log', { error: err.message });
    next(err);
  }
}

export async function getAccessPolicy(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await proxyToModule(`/api/v1/server-manager/${communityId}/servers/${serverId}/policy`);
    res.json(result);
  } catch (err) {
    logger.error('Failed to get access policy', { error: err.message });
    next(err);
  }
}

export async function updateAccessPolicy(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/policy`,
      'PUT',
      req.body
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to update access policy', { error: err.message });
    next(err);
  }
}

export async function triggerEnforcement(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/enforce`,
      'POST'
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to trigger enforcement', { error: err.message });
    next(err);
  }
}

export async function getAccessLog(req, res, next) {
  try {
    const { communityId, serverId } = req.params;
    const { limit = 50, offset = 0 } = req.query;
    const result = await proxyToModule(
      `/api/v1/server-manager/${communityId}/servers/${serverId}/access-log?limit=${limit}&offset=${offset}`
    );
    res.json(result);
  } catch (err) {
    logger.error('Failed to get access log', { error: err.message });
    next(err);
  }
}
