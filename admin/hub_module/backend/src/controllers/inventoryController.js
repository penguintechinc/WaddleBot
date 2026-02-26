/**
 * Inventory (Quartermaster) Controller
 * Handles CRUD for inventory items, checkouts, stock management, and audit log
 */
import { query } from '../config/database.js';
import logger from '../utils/logger.js';

// ── Admin Functions ────────────────────────────────────────────

/**
 * List all inventory items for a community
 */
export async function listItems(req, res, next) {
  try {
    const { communityId } = req.params;
    const result = await query(
      `SELECT id, name, description, item_type, category, quantity,
              available_quantity, metadata, created_at, updated_at
       FROM inventory_items
       WHERE community_id = $1 AND deleted_at IS NULL
       ORDER BY category ASC, name ASC`,
      [communityId]
    );
    res.json({ items: result.rows });
  } catch (err) {
    logger.error('Failed to list inventory items', { error: err.message });
    next(err);
  }
}

/**
 * Create a new inventory item
 */
export async function createItem(req, res, next) {
  try {
    const { communityId } = req.params;
    const { name, description, item_type, category, quantity, metadata } = req.body;

    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Item name is required' });
    }
    if (!quantity || isNaN(parseInt(quantity)) || parseInt(quantity) < 0) {
      return res.status(400).json({ error: 'Quantity must be a non-negative number' });
    }

    const qty = parseInt(quantity);
    const result = await query(
      `INSERT INTO inventory_items
         (community_id, name, description, item_type, category, quantity, available_quantity, metadata)
       VALUES ($1, $2, $3, $4, $5, $6, $6, $7)
       RETURNING *`,
      [
        communityId,
        name.trim(),
        description || null,
        item_type || 'general',
        category || null,
        qty,
        JSON.stringify(metadata || {})
      ]
    );
    res.status(201).json({ item: result.rows[0] });
  } catch (err) {
    logger.error('Failed to create inventory item', { error: err.message });
    next(err);
  }
}

/**
 * Update an inventory item
 */
export async function updateItem(req, res, next) {
  try {
    const { communityId, itemId } = req.params;
    const { name, description, item_type, category, metadata } = req.body;

    const result = await query(
      `UPDATE inventory_items
       SET name        = COALESCE($1, name),
           description = COALESCE($2, description),
           item_type   = COALESCE($3, item_type),
           category    = COALESCE($4, category),
           metadata    = COALESCE($5, metadata),
           updated_at  = NOW()
       WHERE id = $6 AND community_id = $7 AND deleted_at IS NULL
       RETURNING *`,
      [
        name ? name.trim() : null,
        description,
        item_type || null,
        category || null,
        metadata ? JSON.stringify(metadata) : null,
        itemId,
        communityId
      ]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found' });
    }
    res.json({ item: result.rows[0] });
  } catch (err) {
    logger.error('Failed to update inventory item', { error: err.message });
    next(err);
  }
}

/**
 * Soft-delete an inventory item
 */
export async function deleteItem(req, res, next) {
  try {
    const { communityId, itemId } = req.params;
    const result = await query(
      `UPDATE inventory_items
       SET deleted_at = NOW()
       WHERE id = $1 AND community_id = $2 AND deleted_at IS NULL
       RETURNING id`,
      [itemId, communityId]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found' });
    }
    res.json({ message: 'Item deleted' });
  } catch (err) {
    logger.error('Failed to delete inventory item', { error: err.message });
    next(err);
  }
}

/**
 * Add stock to an item
 */
export async function addStock(req, res, next) {
  try {
    const { communityId, itemId } = req.params;
    const { quantity, notes } = req.body;

    if (!quantity || isNaN(parseInt(quantity)) || parseInt(quantity) <= 0) {
      return res.status(400).json({ error: 'Quantity must be a positive number' });
    }

    // Verify item belongs to community
    const check = await query(
      'SELECT id FROM inventory_items WHERE id = $1 AND community_id = $2 AND deleted_at IS NULL',
      [itemId, communityId]
    );
    if (check.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found' });
    }

    const result = await query(
      'SELECT * FROM add_inventory_stock($1, $2, $3, $4)',
      [itemId, req.user.id, parseInt(quantity), notes || null]
    );
    res.json({ item: result.rows[0] });
  } catch (err) {
    logger.error('Failed to add inventory stock', { error: err.message });
    next(err);
  }
}

/**
 * Remove stock from an item
 */
export async function removeStock(req, res, next) {
  try {
    const { communityId, itemId } = req.params;
    const { quantity, notes } = req.body;

    if (!quantity || isNaN(parseInt(quantity)) || parseInt(quantity) <= 0) {
      return res.status(400).json({ error: 'Quantity must be a positive number' });
    }

    const check = await query(
      'SELECT id FROM inventory_items WHERE id = $1 AND community_id = $2 AND deleted_at IS NULL',
      [itemId, communityId]
    );
    if (check.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found' });
    }

    const result = await query(
      'SELECT * FROM remove_inventory_stock($1, $2, $3, $4)',
      [itemId, req.user.id, parseInt(quantity), notes || null]
    );
    res.json({ item: result.rows[0] });
  } catch (err) {
    logger.error('Failed to remove inventory stock', { error: err.message });
    next(err);
  }
}

/**
 * List all checkouts for a community (admin view)
 */
export async function listAllCheckouts(req, res, next) {
  try {
    const { communityId } = req.params;
    const { status } = req.query;

    const conditions = ['ii.community_id = $1', 'ii.deleted_at IS NULL'];
    const params = [communityId];
    let idx = 2;

    if (status) {
      conditions.push(`ic.status = $${idx++}`);
      params.push(status);
    }

    const where = conditions.join(' AND ');

    const result = await query(
      `SELECT ic.id, ic.item_id, ic.user_id, ic.quantity_checked_out,
              ic.due_date, ic.status, ic.notes, ic.checked_out_at, ic.returned_at,
              ii.name as item_name, ii.category as item_category,
              hu.display_name as user_name, hu.email as user_email
       FROM inventory_checkouts ic
       JOIN inventory_items ii ON ic.item_id = ii.id
       JOIN hub_users hu ON ic.user_id = hu.id
       WHERE ${where}
       ORDER BY ic.checked_out_at DESC`,
      params
    );

    res.json({ checkouts: result.rows });
  } catch (err) {
    logger.error('Failed to list inventory checkouts', { error: err.message });
    next(err);
  }
}

/**
 * Get inventory summary for a community
 */
export async function getSummary(req, res, next) {
  try {
    const { communityId } = req.params;
    const result = await query(
      'SELECT * FROM get_inventory_summary($1)',
      [communityId]
    );
    res.json({ summary: result.rows[0] || {} });
  } catch (err) {
    logger.error('Failed to get inventory summary', { error: err.message });
    next(err);
  }
}

/**
 * Get inventory audit log
 */
export async function getAuditLog(req, res, next) {
  try {
    const { communityId } = req.params;
    const { item_id, action, limit = 50, offset = 0 } = req.query;

    const conditions = ['ii.community_id = $1'];
    const params = [communityId];
    let idx = 2;

    if (item_id) {
      conditions.push(`il.item_id = $${idx++}`);
      params.push(item_id);
    }
    if (action) {
      conditions.push(`il.action = $${idx++}`);
      params.push(action);
    }

    const where = conditions.join(' AND ');

    const result = await query(
      `SELECT il.id, il.item_id, il.action, il.quantity_delta,
              il.previous_quantity, il.new_quantity, il.notes,
              il.created_at, il.performed_by_user_id,
              ii.name as item_name,
              hu.display_name as performed_by_name
       FROM inventory_log il
       JOIN inventory_items ii ON il.item_id = ii.id
       LEFT JOIN hub_users hu ON il.performed_by_user_id = hu.id
       WHERE ${where}
       ORDER BY il.created_at DESC
       LIMIT $${idx++} OFFSET $${idx++}`,
      [...params, parseInt(limit), parseInt(offset)]
    );

    res.json({ log: result.rows });
  } catch (err) {
    logger.error('Failed to get inventory audit log', { error: err.message });
    next(err);
  }
}

// ── Member Functions ───────────────────────────────────────────

/**
 * List available items (available_quantity > 0)
 */
export async function listAvailable(req, res, next) {
  try {
    const { communityId } = req.params;
    const { search } = req.query;

    if (search) {
      const result = await query(
        'SELECT * FROM search_inventory_items($1, $2)',
        [communityId, search]
      );
      return res.json({ items: result.rows });
    }

    const result = await query(
      `SELECT id, name, description, item_type, category,
              quantity, available_quantity, metadata
       FROM inventory_items
       WHERE community_id = $1
         AND deleted_at IS NULL
         AND available_quantity > 0
       ORDER BY category ASC, name ASC`,
      [communityId]
    );
    res.json({ items: result.rows });
  } catch (err) {
    logger.error('Failed to list available inventory', { error: err.message });
    next(err);
  }
}

/**
 * Check out an item (member claim)
 */
export async function checkoutItem(req, res, next) {
  try {
    const { communityId } = req.params;
    const { item_id, quantity, due_date, notes } = req.body;

    if (!item_id) {
      return res.status(400).json({ error: 'item_id is required' });
    }
    if (!quantity || isNaN(parseInt(quantity)) || parseInt(quantity) <= 0) {
      return res.status(400).json({ error: 'Quantity must be a positive number' });
    }

    // Verify item belongs to this community
    const check = await query(
      'SELECT id, available_quantity FROM inventory_items WHERE id = $1 AND community_id = $2 AND deleted_at IS NULL',
      [item_id, communityId]
    );
    if (check.rows.length === 0) {
      return res.status(404).json({ error: 'Item not found' });
    }
    if (check.rows[0].available_quantity < parseInt(quantity)) {
      return res.status(409).json({ error: 'Insufficient available quantity' });
    }

    const result = await query(
      'SELECT * FROM update_inventory_on_checkout($1, $2, $3, $4, $5)',
      [item_id, req.user.id, parseInt(quantity), due_date || null, notes || null]
    );
    res.status(201).json({ checkout: result.rows[0] });
  } catch (err) {
    logger.error('Failed to checkout inventory item', { error: err.message });
    next(err);
  }
}

/**
 * Return a checked-out item
 */
export async function checkinItem(req, res, next) {
  try {
    const { communityId } = req.params;
    const { checkout_id, quantity_returned, notes } = req.body;

    if (!checkout_id) {
      return res.status(400).json({ error: 'checkout_id is required' });
    }

    // Verify checkout belongs to this user and community
    const check = await query(
      `SELECT ic.id, ic.quantity_checked_out
       FROM inventory_checkouts ic
       JOIN inventory_items ii ON ic.item_id = ii.id
       WHERE ic.id = $1 AND ic.user_id = $2 AND ii.community_id = $3
         AND ic.status = 'active'`,
      [checkout_id, req.user.id, communityId]
    );
    if (check.rows.length === 0) {
      return res.status(404).json({ error: 'Active checkout not found' });
    }

    const qty = quantity_returned
      ? parseInt(quantity_returned)
      : check.rows[0].quantity_checked_out;

    const result = await query(
      'SELECT * FROM update_inventory_on_return($1, $2, $3, $4)',
      [checkout_id, req.user.id, qty, notes || null]
    );
    res.json({ checkout: result.rows[0] });
  } catch (err) {
    logger.error('Failed to checkin inventory item', { error: err.message });
    next(err);
  }
}

/**
 * Get current user's active checkouts
 */
export async function getMyCheckouts(req, res, next) {
  try {
    const { communityId } = req.params;
    const result = await query(
      `SELECT ic.id, ic.item_id, ic.quantity_checked_out, ic.due_date,
              ic.status, ic.notes, ic.checked_out_at,
              ii.name as item_name, ii.category as item_category
       FROM inventory_checkouts ic
       JOIN inventory_items ii ON ic.item_id = ii.id
       WHERE ii.community_id = $1
         AND ic.user_id = $2
         AND ic.status = 'active'
       ORDER BY ic.checked_out_at DESC`,
      [communityId, req.user.id]
    );
    res.json({ checkouts: result.rows });
  } catch (err) {
    logger.error('Failed to get my checkouts', { error: err.message });
    next(err);
  }
}
