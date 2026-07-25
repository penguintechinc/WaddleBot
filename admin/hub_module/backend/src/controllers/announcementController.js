/**
 * Announcement Controller - Community announcement management
 * Handles creating, updating, retrieving, and broadcasting announcements.
 */
import { query } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';
import * as broadcastService from '../services/broadcastService.js';

// Valid announcement types
const VALID_ANNOUNCEMENT_TYPES = ['general', 'important', 'event', 'update'];

// Valid announcement statuses
const VALID_STATUSES = ['draft', 'published', 'archived'];

/**
 * Get paginated list of announcements for a community
 * GET /api/v1/communities/:communityId/announcements
 */
export async function getAnnouncements(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(100, Math.max(1, parseInt(req.query.limit || '20', 10)));
    const offset = (page - 1) * limit;
    const statusFilter = req.query.status;
    const pinnedFilter = req.query.pinned;

    // Build WHERE clause
    let whereClause = 'WHERE community_id = $1';
    const params = [communityId];
    let paramIndex = 2;

    if (statusFilter && VALID_STATUSES.includes(statusFilter)) {
      whereClause += ` AND status = $${paramIndex}`;
      params.push(statusFilter);
      paramIndex++;
    }

    if (pinnedFilter === 'true') {
      whereClause += ` AND is_pinned = true`;
    } else if (pinnedFilter === 'false') {
      whereClause += ` AND is_pinned = false`;
    }

    // Get total count
    const countResult = await query(
      `SELECT COUNT(*) as count FROM announcements ${whereClause}`,
      params
    );
    const total = parseInt(countResult.rows[0]?.count || 0, 10);

    // Get paginated results - pinned first, then by created_at DESC
    const result = await query(
      `SELECT id, community_id, title, content, announcement_type, status,
              is_pinned, created_by, created_by_name, created_at,
              updated_by, updated_at, published_at, archived_at
       FROM announcements
       ${whereClause}
       ORDER BY is_pinned DESC, created_at DESC
       LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`,
      [...params, limit, offset]
    );

    const announcements = result.rows.map(formatAnnouncement);

    res.json({
      success: true,
      data: announcements,
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
 * Get single announcement by ID
 * GET /api/v1/communities/:communityId/announcements/:announcementId
 */
export async function getAnnouncement(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    const result = await query(
      `SELECT id, community_id, title, content, announcement_type, status,
              is_pinned, created_by, created_by_name, created_at,
              updated_by, updated_at, published_at, archived_at
       FROM announcements
       WHERE id = $1 AND community_id = $2`,
      [announcementId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Create new announcement
 * POST /api/v1/communities/:communityId/announcements
 */
export async function createAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const { title, content, announcement_type, is_pinned, status } = req.body;

    // Validate inputs
    if (!title || typeof title !== 'string' || title.trim().length === 0) {
      return next(errors.badRequest('Title is required'));
    }

    if (title.length > 255) {
      return next(errors.badRequest('Title must be 255 characters or less'));
    }

    if (!content || typeof content !== 'string' || content.trim().length === 0) {
      return next(errors.badRequest('Content is required'));
    }

    if (content.length > 2000) {
      return next(errors.badRequest('Content must be 2000 characters or less'));
    }

    const finalAnnouncementType = announcement_type || 'general';
    if (!VALID_ANNOUNCEMENT_TYPES.includes(finalAnnouncementType)) {
      return next(errors.badRequest(
        `Invalid announcement_type. Must be one of: ${VALID_ANNOUNCEMENT_TYPES.join(', ')}`
      ));
    }

    const finalIsPinned = is_pinned === true;
    const finalStatus = status || 'draft';

    if (!VALID_STATUSES.includes(finalStatus)) {
      return next(errors.badRequest(
        `Invalid status. Must be one of: ${VALID_STATUSES.join(', ')}`
      ));
    }

    // Create announcement
    const publishedAt = finalStatus === 'published' ? new Date() : null;

    const result = await query(
      `INSERT INTO announcements (
        community_id, title, content, announcement_type, status,
        is_pinned, created_by, created_by_name, created_at, published_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9)
      RETURNING id, community_id, title, content, announcement_type, status,
                is_pinned, created_by, created_by_name, created_at,
                updated_by, updated_at, published_at, archived_at`,
      [
        communityId,
        title.trim(),
        content.trim(),
        finalAnnouncementType,
        finalStatus,
        finalIsPinned,
        req.user.userId,
        req.user.username || '',
        publishedAt,
      ]
    );

    logger.audit('Announcement created', {
      communityId,
      announcementId: result.rows[0].id,
      userId: req.user.userId,
      username: req.user.username,
      title,
    });

    res.status(201).json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Update existing announcement
 * PUT /api/v1/communities/:communityId/announcements/:announcementId
 */
export async function updateAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);
    const { title, content, announcement_type, is_pinned, status } = req.body;

    // Validate inputs (all optional, but must be valid if provided)
    if (title !== undefined) {
      if (typeof title !== 'string' || title.trim().length === 0) {
        return next(errors.badRequest('Title must be a non-empty string'));
      }
      if (title.length > 255) {
        return next(errors.badRequest('Title must be 255 characters or less'));
      }
    }

    if (content !== undefined) {
      if (typeof content !== 'string' || content.trim().length === 0) {
        return next(errors.badRequest('Content must be a non-empty string'));
      }
      if (content.length > 2000) {
        return next(errors.badRequest('Content must be 2000 characters or less'));
      }
    }

    if (announcement_type !== undefined) {
      if (!VALID_ANNOUNCEMENT_TYPES.includes(announcement_type)) {
        return next(errors.badRequest(
          `Invalid announcement_type. Must be one of: ${VALID_ANNOUNCEMENT_TYPES.join(', ')}`
        ));
      }
    }

    if (status !== undefined) {
      if (!VALID_STATUSES.includes(status)) {
        return next(errors.badRequest(
          `Invalid status. Must be one of: ${VALID_STATUSES.join(', ')}`
        ));
      }
    }

    // Get current announcement
    const currentResult = await query(
      `SELECT id, status, published_at FROM announcements
       WHERE id = $1 AND community_id = $2`,
      [announcementId, communityId]
    );

    if (currentResult.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    const current = currentResult.rows[0];

    // Determine if we need to set published_at
    let publishedAt = current.published_at;
    if (status === 'published' && current.published_at === null) {
      publishedAt = new Date();
    }

    // Build UPDATE query dynamically
    const updates = [];
    const params = [];
    let paramIndex = 1;

    if (title !== undefined) {
      updates.push(`title = $${paramIndex}`);
      params.push(title.trim());
      paramIndex++;
    }

    if (content !== undefined) {
      updates.push(`content = $${paramIndex}`);
      params.push(content.trim());
      paramIndex++;
    }

    if (announcement_type !== undefined) {
      updates.push(`announcement_type = $${paramIndex}`);
      params.push(announcement_type);
      paramIndex++;
    }

    if (is_pinned !== undefined) {
      updates.push(`is_pinned = $${paramIndex}`);
      params.push(is_pinned === true);
      paramIndex++;
    }

    if (status !== undefined) {
      updates.push(`status = $${paramIndex}`);
      params.push(status);
      paramIndex++;
    }

    updates.push(`updated_by = $${paramIndex}`);
    params.push(req.user.userId);
    paramIndex++;

    updates.push(`updated_at = NOW()`);

    if (publishedAt !== current.published_at) {
      updates.push(`published_at = $${paramIndex}`);
      params.push(publishedAt);
      paramIndex++;
    }

    // Add announcement ID and community ID to where clause
    params.push(announcementId);
    params.push(communityId);

    const result = await query(
      `UPDATE announcements
       SET ${updates.join(', ')}
       WHERE id = $${paramIndex} AND community_id = $${paramIndex + 1}
       RETURNING id, community_id, title, content, announcement_type, status,
                 is_pinned, created_by, created_by_name, created_at,
                 updated_by, updated_at, published_at, archived_at`,
      params
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    logger.audit('Announcement updated', {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
      changes: Object.keys({ title, content, announcement_type, is_pinned, status })
        .filter(key => eval(key) !== undefined),
    });

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Delete announcement (soft delete)
 * DELETE /api/v1/communities/:communityId/announcements/:announcementId
 */
export async function deleteAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    const result = await query(
      `UPDATE announcements
       SET status = 'archived', archived_at = NOW(), updated_by = $1, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING id, community_id, title, content, announcement_type, status,
                 is_pinned, created_by, created_by_name, created_at,
                 updated_by, updated_at, published_at, archived_at`,
      [req.user.userId, announcementId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    logger.audit('Announcement deleted (archived)', {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
    });

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Publish a draft announcement
 * POST /api/v1/communities/:communityId/announcements/:announcementId/publish
 */
export async function publishAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    // Get current announcement
    const currentResult = await query(
      `SELECT status FROM announcements WHERE id = $1 AND community_id = $2`,
      [announcementId, communityId]
    );

    if (currentResult.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    const result = await query(
      `UPDATE announcements
       SET status = 'published', published_at = NOW(), updated_by = $1, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING id, community_id, title, content, announcement_type, status,
                 is_pinned, created_by, created_by_name, created_at,
                 updated_by, updated_at, published_at, archived_at`,
      [req.user.userId, announcementId, communityId]
    );

    logger.audit('Announcement published', {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
    });

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Toggle pin status of announcement
 * POST /api/v1/communities/:communityId/announcements/:announcementId/pin
 */
export async function pinAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    // Get current pin status
    const currentResult = await query(
      `SELECT is_pinned FROM announcements WHERE id = $1 AND community_id = $2`,
      [announcementId, communityId]
    );

    if (currentResult.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    const newPinState = !currentResult.rows[0].is_pinned;

    const result = await query(
      `UPDATE announcements
       SET is_pinned = $1, updated_by = $2, updated_at = NOW()
       WHERE id = $3 AND community_id = $4
       RETURNING id, community_id, title, content, announcement_type, status,
                 is_pinned, created_by, created_by_name, created_at,
                 updated_by, updated_at, published_at, archived_at`,
      [newPinState, req.user.userId, announcementId, communityId]
    );

    logger.audit(`Announcement ${newPinState ? 'pinned' : 'unpinned'}`, {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
      isPinned: newPinState,
    });

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Unpin an announcement
 * PUT /api/v1/communities/:communityId/announcements/:announcementId/unpin
 */
export async function unpinAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    const result = await query(
      `UPDATE announcements
       SET is_pinned = false, updated_by = $1, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING id, community_id, title, content, announcement_type, status,
                 is_pinned, created_by, created_by_name, created_at,
                 updated_by, updated_at, published_at, archived_at`,
      [req.user.userId, announcementId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    logger.audit('Announcement unpinned', {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
    });

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Archive an announcement
 * POST /api/v1/communities/:communityId/announcements/:announcementId/archive
 */
export async function archiveAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    const result = await query(
      `UPDATE announcements
       SET status = 'archived', archived_at = NOW(), updated_by = $1, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING id, community_id, title, content, announcement_type, status,
                 is_pinned, created_by, created_by_name, created_at,
                 updated_by, updated_at, published_at, archived_at`,
      [req.user.userId, announcementId, communityId]
    );

    if (result.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    logger.audit('Announcement archived', {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
    });

    res.json({
      success: true,
      data: formatAnnouncement(result.rows[0]),
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Broadcast announcement to platforms
 * POST /api/v1/communities/:communityId/announcements/:announcementId/broadcast
 */
export async function broadcastAnnouncement(req, res, next) {
  try {
    if (!req.user?.userId) {
      return next(errors.unauthorized());
    }

    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);
    const { platforms } = req.body;

    if (!Array.isArray(platforms) || platforms.length === 0) {
      return next(errors.badRequest('Platforms array is required and must not be empty'));
    }

    // Validate announcement exists and is published
    const announcementResult = await query(
      `SELECT id, title, content, status FROM announcements
       WHERE id = $1 AND community_id = $2`,
      [announcementId, communityId]
    );

    if (announcementResult.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    if (announcementResult.rows[0].status !== 'published') {
      return next(errors.badRequest('Only published announcements can be broadcast'));
    }

    // Get full announcement data
    const announcement = announcementResult.rows[0];

    // Broadcast to all requested platforms
    const broadcastResults = await broadcastService.broadcastToAllPlatforms(
      communityId,
      {
        id: announcementId,
        title: announcement.title,
        content: announcement.content,
      },
      req.user.userId,
      platforms
    );

    logger.audit('Announcement broadcast initiated', {
      communityId,
      announcementId,
      userId: req.user.userId,
      username: req.user.username,
      platforms,
      results: broadcastResults,
    });

    res.json({
      success: true,
      data: {
        announcementId,
        platforms,
        results: broadcastResults,
        status: 'initiated',
        message: 'Broadcast initiated. Use broadcast status endpoint to check progress.',
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Get broadcast status for an announcement
 * GET /api/v1/communities/:communityId/announcements/:announcementId/broadcast-status
 */
export async function getBroadcastStatus(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const announcementId = parseInt(req.params.announcementId, 10);

    // Verify announcement exists
    const announcementResult = await query(
      `SELECT id FROM announcements WHERE id = $1 AND community_id = $2`,
      [announcementId, communityId]
    );

    if (announcementResult.rows.length === 0) {
      return next(errors.notFound('Announcement not found'));
    }

    // Get broadcast records
    const result = await query(
      `SELECT id, announcement_id, platform, status, broadcast_at,
              completed_at, error_message
       FROM announcement_broadcasts
       WHERE announcement_id = $1
       ORDER BY broadcast_at DESC`,
      [announcementId]
    );

    const broadcasts = result.rows.map(row => ({
      id: row.id,
      announcementId: row.announcement_id,
      platform: row.platform,
      status: row.status,
      broadcastAt: row.broadcast_at?.toISOString(),
      completedAt: row.completed_at?.toISOString(),
      errorMessage: row.error_message,
    }));

    res.json({
      success: true,
      data: broadcasts,
    });
  } catch (err) {
    next(err);
  }
}

// Helper functions

/**
 * Format announcement row from database
 */
function formatAnnouncement(row) {
  if (!row) return null;

  return {
    id: row.id,
    communityId: row.community_id,
    title: row.title,
    content: row.content,
    announcementType: row.announcement_type,
    status: row.status,
    isPinned: row.is_pinned,
    createdBy: row.created_by,
    createdByName: row.created_by_name,
    createdAt: row.created_at?.toISOString(),
    updatedBy: row.updated_by,
    updatedAt: row.updated_at?.toISOString(),
    publishedAt: row.published_at?.toISOString(),
    archivedAt: row.archived_at?.toISOString(),
  };
}

export default {
  getAnnouncements,
  getAnnouncement,
  createAnnouncement,
  updateAnnouncement,
  deleteAnnouncement,
  publishAnnouncement,
  pinAnnouncement,
  unpinAnnouncement,
  archiveAnnouncement,
  broadcastAnnouncement,
  getBroadcastStatus,
};
