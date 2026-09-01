/**
 * Join Request Controller
 * Handles community join requests for approval-mode communities
 */
import { query } from '../config/database.js';
import { errors } from '../middleware/errorHandler.js';
import { logger } from '../utils/logger.js';

/**
 * Submit a join request (member action)
 * POST /community/:communityId/join-requests
 */
export async function submitRequest(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());
    const communityId = parseInt(req.params.communityId, 10);
    const { message } = req.body;

    // Verify community is in approval mode
    const comm = await query(
      'SELECT id, join_mode FROM communities WHERE id = $1',
      [communityId]
    );
    if (!comm.rows.length) return next(errors.notFound('Community not found'));
    if (comm.rows[0].join_mode !== 'approval') {
      return next(errors.badRequest('This community does not require approval to join'));
    }

    // Check already a member
    const existing = await query(
      'SELECT id FROM community_members WHERE community_id = $1 AND user_id = $2',
      [communityId, req.user.userId]
    );
    if (existing.rows.length) return next(errors.conflict('Already a member'));

    // Upsert join request (reset if previously rejected)
    const result = await query(
      `INSERT INTO community_join_requests (community_id, user_id, status, message)
       VALUES ($1, $2, 'pending', $3)
       ON CONFLICT (community_id, user_id) DO UPDATE
         SET status = 'pending', message = EXCLUDED.message, reviewed_by = NULL, reviewed_at = NULL
       RETURNING id, status, created_at`,
      [communityId, req.user.userId, message || null]
    );

    res.status(201).json({ success: true, request: result.rows[0] });
  } catch (err) {
    next(err);
  }
}

/**
 * Get current user's join request status
 * GET /community/:communityId/join-requests/mine
 */
export async function getMyRequest(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());
    const communityId = parseInt(req.params.communityId, 10);
    const result = await query(
      'SELECT id, status, message, created_at, reviewed_at FROM community_join_requests WHERE community_id = $1 AND user_id = $2',
      [communityId, req.user.userId]
    );
    res.json({ success: true, request: result.rows[0] || null });
  } catch (err) {
    next(err);
  }
}

/**
 * List pending join requests (admin)
 * GET /admin/:communityId/join-requests
 */
export async function listRequests(req, res, next) {
  try {
    const communityId = parseInt(req.params.communityId, 10);
    const status = req.query.status || 'pending';
    const page = Math.max(1, parseInt(req.query.page || '1', 10));
    const limit = Math.min(50, Math.max(1, parseInt(req.query.limit || '25', 10)));
    const offset = (page - 1) * limit;

    const result = await query(
      `SELECT r.id, r.status, r.message, r.created_at, r.reviewed_at,
              u.username, u.email, u.avatar_url as "avatarUrl"
       FROM community_join_requests r
       JOIN hub_users u ON u.id = r.user_id
       WHERE r.community_id = $1 AND r.status = $2
       ORDER BY r.created_at ASC
       LIMIT $3 OFFSET $4`,
      [communityId, status, limit, offset]
    );

    const countRes = await query(
      'SELECT COUNT(*) FROM community_join_requests WHERE community_id = $1 AND status = $2',
      [communityId, status]
    );

    res.json({
      success: true,
      requests: result.rows,
      pagination: {
        total: parseInt(countRes.rows[0].count, 10),
        page,
        limit,
        totalPages: Math.ceil(parseInt(countRes.rows[0].count, 10) / limit),
      },
    });
  } catch (err) {
    next(err);
  }
}

/**
 * Approve a join request (admin)
 * PUT /admin/:communityId/join-requests/:requestId/approve
 */
export async function approveRequest(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());
    const communityId = parseInt(req.params.communityId, 10);
    const requestId = parseInt(req.params.requestId, 10);

    const reqRow = await query(
      'SELECT user_id FROM community_join_requests WHERE id = $1 AND community_id = $2 AND status = $3',
      [requestId, communityId, 'pending']
    );
    if (!reqRow.rows.length) return next(errors.notFound('Pending request not found'));
    const { user_id: userId } = reqRow.rows[0];

    // Add member
    await query(
      `INSERT INTO community_members (community_id, user_id, role, joined_at)
       VALUES ($1, $2, 'member', NOW())
       ON CONFLICT (community_id, user_id) DO NOTHING`,
      [communityId, userId]
    );

    // Update request status
    await query(
      `UPDATE community_join_requests
       SET status = 'approved', reviewed_by = $1, reviewed_at = NOW()
       WHERE id = $2`,
      [req.user.userId, requestId]
    );

    logger.audit('Join request approved', { communityId, requestId, reviewerId: req.user.userId });
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}

/**
 * Reject a join request (admin)
 * PUT /admin/:communityId/join-requests/:requestId/reject
 */
export async function rejectRequest(req, res, next) {
  try {
    if (!req.user?.userId) return next(errors.unauthorized());
    const communityId = parseInt(req.params.communityId, 10);
    const requestId = parseInt(req.params.requestId, 10);

    const updated = await query(
      `UPDATE community_join_requests
       SET status = 'rejected', reviewed_by = $1, reviewed_at = NOW()
       WHERE id = $2 AND community_id = $3 AND status = 'pending'
       RETURNING id`,
      [req.user.userId, requestId, communityId]
    );
    if (!updated.rows.length) return next(errors.notFound('Pending request not found'));

    logger.audit('Join request rejected', { communityId, requestId, reviewerId: req.user.userId });
    res.json({ success: true });
  } catch (err) {
    next(err);
  }
}
