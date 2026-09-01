/**
 * Support Ticket System Controller
 * Handles CRUD for categories, tickets, comments, and stats
 */
import { query } from '../config/database.js';
import logger from '../utils/logger.js';

/**
 * Get all categories for a community
 */
export async function getCategories(req, res, next) {
  try {
    const { communityId } = req.params;
    const result = await query(
      `SELECT id, name, description, sort_order, is_active, form_fields, created_at
       FROM support_ticket_categories
       WHERE community_id = $1
       ORDER BY sort_order ASC, name ASC`,
      [communityId]
    );
    res.json({ categories: result.rows });
  } catch (err) {
    logger.error('Failed to get support categories', { error: err.message });
    next(err);
  }
}

/**
 * Create a new category
 */
export async function createCategory(req, res, next) {
  try {
    const { communityId } = req.params;
    const { name, description, sort_order, form_fields } = req.body;

    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Category name is required' });
    }

    const result = await query(
      `INSERT INTO support_ticket_categories (community_id, name, description, sort_order, form_fields)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [communityId, name.trim(), description || null, sort_order || 0, JSON.stringify(form_fields || [])]
    );
    res.status(201).json({ category: result.rows[0] });
  } catch (err) {
    logger.error('Failed to create support category', { error: err.message });
    next(err);
  }
}

/**
 * Update a category
 */
export async function updateCategory(req, res, next) {
  try {
    const { communityId, categoryId } = req.params;
    const { name, description, sort_order, is_active, form_fields } = req.body;

    const result = await query(
      `UPDATE support_ticket_categories
       SET name = COALESCE($1, name),
           description = COALESCE($2, description),
           sort_order = COALESCE($3, sort_order),
           is_active = COALESCE($4, is_active),
           form_fields = COALESCE($5, form_fields)
       WHERE id = $6 AND community_id = $7
       RETURNING *`,
      [name || null, description, sort_order, is_active, form_fields ? JSON.stringify(form_fields) : null, categoryId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Category not found' });
    }
    res.json({ category: result.rows[0] });
  } catch (err) {
    logger.error('Failed to update support category', { error: err.message });
    next(err);
  }
}

/**
 * Delete a category
 */
export async function deleteCategory(req, res, next) {
  try {
    const { communityId, categoryId } = req.params;
    const result = await query(
      'DELETE FROM support_ticket_categories WHERE id = $1 AND community_id = $2 RETURNING id',
      [categoryId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Category not found' });
    }
    res.json({ message: 'Category deleted' });
  } catch (err) {
    logger.error('Failed to delete support category', { error: err.message });
    next(err);
  }
}

/**
 * List tickets with filters and pagination
 */
export async function listTickets(req, res, next) {
  try {
    const { communityId } = req.params;
    const { status, priority, category_id, assignee_user_id, search, limit = 25, offset = 0 } = req.query;

    const conditions = ['t.community_id = $1'];
    const params = [communityId];
    let idx = 2;

    if (status) {
      conditions.push(`t.status = $${idx++}`);
      params.push(status);
    }
    if (priority) {
      conditions.push(`t.priority = $${idx++}`);
      params.push(priority);
    }
    if (category_id) {
      conditions.push(`t.category_id = $${idx++}`);
      params.push(category_id);
    }
    if (assignee_user_id) {
      conditions.push(`t.assignee_user_id = $${idx++}`);
      params.push(assignee_user_id);
    }
    if (search) {
      conditions.push(`(t.subject ILIKE $${idx} OR t.ticket_number ILIKE $${idx})`);
      params.push(`%${search}%`);
      idx++;
    }

    const where = conditions.join(' AND ');

    const countResult = await query(
      `SELECT COUNT(*) FROM support_tickets t WHERE ${where}`,
      params
    );

    const ticketsResult = await query(
      `SELECT t.*, c.name as category_name
       FROM support_tickets t
       LEFT JOIN support_ticket_categories c ON t.category_id = c.id
       WHERE ${where}
       ORDER BY
         CASE t.priority
           WHEN 'critical' THEN 0
           WHEN 'high' THEN 1
           WHEN 'medium' THEN 2
           WHEN 'low' THEN 3
           ELSE 4
         END,
         t.updated_at DESC
       LIMIT $${idx++} OFFSET $${idx++}`,
      [...params, parseInt(limit), parseInt(offset)]
    );

    res.json({
      tickets: ticketsResult.rows,
      total: parseInt(countResult.rows[0].count),
      limit: parseInt(limit),
      offset: parseInt(offset)
    });
  } catch (err) {
    logger.error('Failed to list support tickets', { error: err.message });
    next(err);
  }
}

/**
 * Get a single ticket with comments
 */
export async function getTicket(req, res, next) {
  try {
    const { communityId, ticketId } = req.params;

    const ticketResult = await query(
      `SELECT t.*, c.name as category_name
       FROM support_tickets t
       LEFT JOIN support_ticket_categories c ON t.category_id = c.id
       WHERE t.id = $1 AND t.community_id = $2`,
      [ticketId, communityId]
    );

    if (ticketResult.rows.length === 0) {
      return res.status(404).json({ error: 'Ticket not found' });
    }

    let commentsQuery = `SELECT * FROM support_ticket_comments WHERE ticket_id = $1`;
    const commentsParams = [ticketId];

    if (!req.isAdmin) {
      commentsQuery += ' AND is_internal = false';
    }
    commentsQuery += ' ORDER BY created_at ASC';

    const commentsResult = await query(commentsQuery, commentsParams);

    res.json({
      ticket: ticketResult.rows[0],
      comments: commentsResult.rows
    });
  } catch (err) {
    logger.error('Failed to get support ticket', { error: err.message });
    next(err);
  }
}

/**
 * Create a new ticket
 */
export async function createTicket(req, res, next) {
  try {
    const { communityId } = req.params;
    const { category_id, subject, description, priority, reporter_name, reporter_email, custom_fields } = req.body;

    if (!subject || !subject.trim()) {
      return res.status(400).json({ error: 'Subject is required' });
    }

    // Generate ticket number
    const countResult = await query(
      'SELECT COUNT(*) FROM support_tickets WHERE community_id = $1',
      [communityId]
    );
    const num = parseInt(countResult.rows[0].count) + 1;
    const ticket_number = `SUP-${String(num).padStart(5, '0')}`;

    const result = await query(
      `INSERT INTO support_tickets
       (community_id, category_id, ticket_number, subject, description, priority, reporter_user_id, reporter_name, reporter_email, custom_fields)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING *`,
      [
        communityId,
        category_id || null,
        ticket_number,
        subject.trim(),
        description || null,
        priority || 'medium',
        req.user?.id || null,
        reporter_name || req.user?.display_name || null,
        reporter_email || req.user?.email || null,
        JSON.stringify(custom_fields || {})
      ]
    );

    res.status(201).json({ ticket: result.rows[0] });
  } catch (err) {
    logger.error('Failed to create support ticket', { error: err.message });
    next(err);
  }
}

/**
 * Update ticket status
 */
export async function updateTicketStatus(req, res, next) {
  try {
    const { communityId, ticketId } = req.params;
    const { status } = req.body;

    const validStatuses = ['open', 'in_progress', 'waiting', 'resolved', 'closed'];
    if (!validStatuses.includes(status)) {
      return res.status(400).json({ error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` });
    }

    const resolvedAt = status === 'resolved' ? 'NOW()' : 'resolved_at';
    const result = await query(
      `UPDATE support_tickets
       SET status = $1, resolved_at = ${status === 'resolved' ? 'NOW()' : 'resolved_at'}, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING *`,
      [status, ticketId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Ticket not found' });
    }
    res.json({ ticket: result.rows[0] });
  } catch (err) {
    logger.error('Failed to update ticket status', { error: err.message });
    next(err);
  }
}

/**
 * Assign ticket to a user
 */
export async function assignTicket(req, res, next) {
  try {
    const { communityId, ticketId } = req.params;
    const { assignee_user_id } = req.body;

    const result = await query(
      `UPDATE support_tickets
       SET assignee_user_id = $1, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING *`,
      [assignee_user_id || null, ticketId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Ticket not found' });
    }
    res.json({ ticket: result.rows[0] });
  } catch (err) {
    logger.error('Failed to assign ticket', { error: err.message });
    next(err);
  }
}

/**
 * Update ticket priority
 */
export async function updateTicketPriority(req, res, next) {
  try {
    const { communityId, ticketId } = req.params;
    const { priority } = req.body;

    const validPriorities = ['low', 'medium', 'high', 'critical'];
    if (!validPriorities.includes(priority)) {
      return res.status(400).json({ error: `Invalid priority. Must be one of: ${validPriorities.join(', ')}` });
    }

    const result = await query(
      `UPDATE support_tickets
       SET priority = $1, updated_at = NOW()
       WHERE id = $2 AND community_id = $3
       RETURNING *`,
      [priority, ticketId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Ticket not found' });
    }
    res.json({ ticket: result.rows[0] });
  } catch (err) {
    logger.error('Failed to update ticket priority', { error: err.message });
    next(err);
  }
}

/**
 * Add a comment to a ticket
 */
export async function addComment(req, res, next) {
  try {
    const { communityId, ticketId } = req.params;
    const { content, is_internal } = req.body;

    if (!content || !content.trim()) {
      return res.status(400).json({ error: 'Comment content is required' });
    }

    // Verify ticket exists
    const ticketCheck = await query(
      'SELECT id FROM support_tickets WHERE id = $1 AND community_id = $2',
      [ticketId, communityId]
    );
    if (ticketCheck.rows.length === 0) {
      return res.status(404).json({ error: 'Ticket not found' });
    }

    const result = await query(
      `INSERT INTO support_ticket_comments (ticket_id, author_user_id, author_name, content, is_internal)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING *`,
      [ticketId, req.user?.id || null, req.user?.display_name || null, content.trim(), is_internal || false]
    );

    // Update ticket timestamp
    await query('UPDATE support_tickets SET updated_at = NOW() WHERE id = $1', [ticketId]);

    res.status(201).json({ comment: result.rows[0] });
  } catch (err) {
    logger.error('Failed to add comment', { error: err.message });
    next(err);
  }
}

/**
 * Get tickets for current user
 */
export async function getMyTickets(req, res, next) {
  try {
    const { communityId } = req.params;

    const result = await query(
      `SELECT t.*, c.name as category_name
       FROM support_tickets t
       LEFT JOIN support_ticket_categories c ON t.category_id = c.id
       WHERE t.community_id = $1 AND t.reporter_user_id = $2
       ORDER BY t.updated_at DESC`,
      [communityId, req.user.id]
    );

    res.json({ tickets: result.rows });
  } catch (err) {
    logger.error('Failed to get my tickets', { error: err.message });
    next(err);
  }
}

/**
 * Get ticket statistics for a community
 */
export async function getTicketStats(req, res, next) {
  try {
    const { communityId } = req.params;

    const result = await query(
      `SELECT
         COUNT(*) as total,
         COUNT(*) FILTER (WHERE status = 'open') as open,
         COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
         COUNT(*) FILTER (WHERE status = 'waiting') as waiting,
         COUNT(*) FILTER (WHERE status = 'resolved') as resolved,
         COUNT(*) FILTER (WHERE status = 'closed') as closed,
         AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))) FILTER (WHERE resolved_at IS NOT NULL) as avg_resolution_seconds
       FROM support_tickets
       WHERE community_id = $1`,
      [communityId]
    );

    const stats = result.rows[0];
    res.json({
      stats: {
        total: parseInt(stats.total),
        open: parseInt(stats.open),
        in_progress: parseInt(stats.in_progress),
        waiting: parseInt(stats.waiting),
        resolved: parseInt(stats.resolved),
        closed: parseInt(stats.closed),
        avg_resolution_seconds: stats.avg_resolution_seconds ? parseFloat(stats.avg_resolution_seconds) : null
      }
    });
  } catch (err) {
    logger.error('Failed to get ticket stats', { error: err.message });
    next(err);
  }
}
