-- Migration 014: Add Quartermaster (Inventory) System
-- Description: Implements inventory management system with item tracking, checkouts, and audit logging
-- Author: Waddles Team
-- Date: 2025-12-15

-- =============================================================================
-- INVENTORY ITEMS TABLE
-- =============================================================================
-- Stores all inventory items that can be managed by the community
CREATE TABLE IF NOT EXISTS inventory_items (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    item_type VARCHAR(100),                                   -- equipment, consumable, collectible, etc.
    category VARCHAR(100),
    quantity INTEGER DEFAULT 0,                               -- Total quantity in inventory
    available_quantity INTEGER DEFAULT 0,                     -- quantity - checked out
    checkout_price INTEGER DEFAULT 0,                         -- community currency cost to checkout
    max_checkout_duration_hours INTEGER,                      -- Maximum checkout duration in hours
    image_url VARCHAR(500),                                   -- Image/thumbnail URL
    metadata JSONB DEFAULT '{}',                              -- Additional custom fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ                                    -- Soft delete support
);

COMMENT ON TABLE inventory_items IS
    'Inventory items that can be checked out by community members. Supports various item types.';

COMMENT ON COLUMN inventory_items.community_id IS
    'Community that owns this inventory item';

COMMENT ON COLUMN inventory_items.name IS
    'Display name of the inventory item';

COMMENT ON COLUMN inventory_items.description IS
    'Detailed description of the inventory item';

COMMENT ON COLUMN inventory_items.item_type IS
    'Type of item: equipment, consumable, collectible, etc.';

COMMENT ON COLUMN inventory_items.category IS
    'Category for organization (e.g., electronics, furniture, sports)';

COMMENT ON COLUMN inventory_items.quantity IS
    'Total quantity available in inventory';

COMMENT ON COLUMN inventory_items.available_quantity IS
    'Quantity available for checkout (quantity - checked out items)';

COMMENT ON COLUMN inventory_items.checkout_price IS
    'Cost in community currency to checkout this item (0 = free)';

COMMENT ON COLUMN inventory_items.max_checkout_duration_hours IS
    'Maximum duration an item can be checked out (NULL = no limit)';

COMMENT ON COLUMN inventory_items.image_url IS
    'URL to item image or thumbnail';

COMMENT ON COLUMN inventory_items.metadata IS
    'Additional custom fields for item-specific data (e.g., {color: "blue", weight: 5})';

COMMENT ON COLUMN inventory_items.deleted_at IS
    'Soft delete timestamp (NULL = active item)';

-- Index for community inventory lookups
CREATE INDEX IF NOT EXISTS idx_inventory_items_community
ON inventory_items(community_id)
WHERE deleted_at IS NULL;

-- Index for active items search
CREATE INDEX IF NOT EXISTS idx_inventory_items_active
ON inventory_items(community_id, created_at DESC)
WHERE deleted_at IS NULL;

-- Index for category/type filtering
CREATE INDEX IF NOT EXISTS idx_inventory_items_category
ON inventory_items(community_id, category, item_type)
WHERE deleted_at IS NULL;

-- Index for low stock queries
CREATE INDEX IF NOT EXISTS idx_inventory_items_stock
ON inventory_items(community_id, available_quantity)
WHERE deleted_at IS NULL AND available_quantity < quantity;

-- Full-text search index on name, description, category, and item_type
CREATE INDEX IF NOT EXISTS idx_inventory_items_search
ON inventory_items USING GIN (to_tsvector('english', name || ' ' || COALESCE(description, '') || ' ' || COALESCE(category, '') || ' ' || COALESCE(item_type, '')))
WHERE deleted_at IS NULL;

COMMENT ON INDEX idx_inventory_items_community IS
    'Efficient lookup of inventory items by community';

COMMENT ON INDEX idx_inventory_items_active IS
    'Efficient retrieval of active inventory items ordered by creation';

COMMENT ON INDEX idx_inventory_items_category IS
    'Efficient filtering by category and item type';

COMMENT ON INDEX idx_inventory_items_stock IS
    'Quick identification of items with limited availability';

COMMENT ON INDEX idx_inventory_items_search IS
    'Full-text search on item names, descriptions, and categories';

-- =============================================================================
-- INVENTORY CHECKOUTS TABLE
-- =============================================================================
-- Tracks item checkouts and returns
CREATE TABLE IF NOT EXISTS inventory_checkouts (
    id SERIAL PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES hub_users(id) ON DELETE RESTRICT,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    checked_out_at TIMESTAMPTZ DEFAULT NOW(),
    due_at TIMESTAMPTZ,
    returned_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'returned', 'overdue')),
    notes TEXT
);

COMMENT ON TABLE inventory_checkouts IS
    'Tracks item checkouts and returns. Maintains audit trail of all checkout activity.';

COMMENT ON COLUMN inventory_checkouts.item_id IS
    'Reference to the checked out inventory item';

COMMENT ON COLUMN inventory_checkouts.user_id IS
    'User who checked out the item';

COMMENT ON COLUMN inventory_checkouts.community_id IS
    'Community context for the checkout';

COMMENT ON COLUMN inventory_checkouts.quantity IS
    'Quantity of the item checked out';

COMMENT ON COLUMN inventory_checkouts.checked_out_at IS
    'Timestamp when the item was checked out';

COMMENT ON COLUMN inventory_checkouts.due_at IS
    'When the item is due to be returned (NULL = no due date)';

COMMENT ON COLUMN inventory_checkouts.returned_at IS
    'Timestamp when the item was returned (NULL = still checked out)';

COMMENT ON COLUMN inventory_checkouts.status IS
    'Current status: active, returned, or overdue';

COMMENT ON COLUMN inventory_checkouts.notes IS
    'Additional notes about the checkout (condition, damage, etc.)';

-- Index for active checkouts
CREATE INDEX IF NOT EXISTS idx_inventory_checkouts_active
ON inventory_checkouts(community_id, status)
WHERE status IN ('active', 'overdue');

-- Index for item lookups
CREATE INDEX IF NOT EXISTS idx_inventory_checkouts_item
ON inventory_checkouts(item_id, status);

-- Index for user checkouts
CREATE INDEX IF NOT EXISTS idx_inventory_checkouts_user
ON inventory_checkouts(user_id, community_id, status);

-- Index for overdue items
CREATE INDEX IF NOT EXISTS idx_inventory_checkouts_overdue
ON inventory_checkouts(community_id, due_at)
WHERE status = 'active';

-- Index for checkout history
CREATE INDEX IF NOT EXISTS idx_inventory_checkouts_history
ON inventory_checkouts(community_id, checked_out_at DESC);

COMMENT ON INDEX idx_inventory_checkouts_active IS
    'Quick lookup of active or overdue checkouts';

COMMENT ON INDEX idx_inventory_checkouts_item IS
    'Find all checkouts for a specific item';

COMMENT ON INDEX idx_inventory_checkouts_user IS
    'Find all checkouts by a specific user';

COMMENT ON INDEX idx_inventory_checkouts_overdue IS
    'Identify overdue items for notifications';

COMMENT ON INDEX idx_inventory_checkouts_history IS
    'Retrieve checkout history for a community';

-- =============================================================================
-- INVENTORY LOG TABLE (AUDIT TRAIL)
-- =============================================================================
-- Immutable audit log for all inventory operations
CREATE TABLE IF NOT EXISTS inventory_log (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES inventory_items(id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES hub_users(id) ON DELETE SET NULL,
    community_id INTEGER NOT NULL REFERENCES communities(id) ON DELETE CASCADE,
    action VARCHAR(50) NOT NULL CHECK (action IN ('checkout', 'return', 'add_stock', 'remove_stock', 'update', 'delete')),
    quantity_change INTEGER,                                  -- Change in quantity (positive or negative)
    details JSONB,                                            -- Additional context about the action
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE inventory_log IS
    'Immutable audit trail for all inventory operations. Used for tracking history and compliance.';

COMMENT ON COLUMN inventory_log.item_id IS
    'Reference to the affected inventory item (NULL if item was deleted)';

COMMENT ON COLUMN inventory_log.user_id IS
    'User who performed the action (NULL if system action)';

COMMENT ON COLUMN inventory_log.community_id IS
    'Community context for the action';

COMMENT ON COLUMN inventory_log.action IS
    'Type of action: checkout, return, add_stock, remove_stock, update, delete';

COMMENT ON COLUMN inventory_log.quantity_change IS
    'Change in inventory quantity (positive = added, negative = removed)';

COMMENT ON COLUMN inventory_log.details IS
    'Additional metadata about the action (e.g., old values, reason, etc.)';

-- Index for community history
CREATE INDEX IF NOT EXISTS idx_inventory_log_community
ON inventory_log(community_id, created_at DESC);

-- Index for item history
CREATE INDEX IF NOT EXISTS idx_inventory_log_item
ON inventory_log(item_id, created_at DESC)
WHERE item_id IS NOT NULL;

-- Index for user actions
CREATE INDEX IF NOT EXISTS idx_inventory_log_user
ON inventory_log(user_id, community_id, created_at DESC)
WHERE user_id IS NOT NULL;

-- Index for action type queries
CREATE INDEX IF NOT EXISTS idx_inventory_log_action
ON inventory_log(community_id, action, created_at DESC);

COMMENT ON INDEX idx_inventory_log_community IS
    'Retrieve audit history for a community';

COMMENT ON INDEX idx_inventory_log_item IS
    'Track complete history of a specific item';

COMMENT ON INDEX idx_inventory_log_user IS
    'Track all actions performed by a user';

COMMENT ON INDEX idx_inventory_log_action IS
    'Retrieve operations of a specific type';

-- =============================================================================
-- HELPER FUNCTIONS
-- =============================================================================

-- Function to update available quantity when item is checked out
CREATE OR REPLACE FUNCTION update_inventory_on_checkout(
    p_item_id INTEGER,
    p_quantity INTEGER,
    p_user_id INTEGER,
    p_community_id INTEGER,
    p_notes TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    new_available_quantity INTEGER,
    message TEXT
) AS $$
DECLARE
    v_current_quantity INTEGER;
    v_available_quantity INTEGER;
BEGIN
    -- Get current quantities
    SELECT quantity, available_quantity INTO v_current_quantity, v_available_quantity
    FROM inventory_items
    WHERE id = p_item_id AND community_id = p_community_id AND deleted_at IS NULL;

    -- Check if sufficient quantity available
    IF v_available_quantity IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, 'Item not found or community mismatch'::TEXT;
        RETURN;
    END IF;

    IF v_available_quantity < p_quantity THEN
        RETURN QUERY SELECT FALSE, v_available_quantity::INTEGER, 'Insufficient quantity available'::TEXT;
        RETURN;
    END IF;

    -- Update available quantity
    UPDATE inventory_items
    SET available_quantity = available_quantity - p_quantity,
        updated_at = NOW()
    WHERE id = p_item_id
    RETURNING available_quantity INTO v_available_quantity;

    -- Create audit log entry
    INSERT INTO inventory_log (item_id, user_id, community_id, action, quantity_change, details)
    VALUES (p_item_id, p_user_id, p_community_id, 'checkout', -p_quantity,
            jsonb_build_object('quantity', p_quantity, 'notes', p_notes));

    RETURN QUERY SELECT TRUE, v_available_quantity::INTEGER, 'Checkout successful'::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_inventory_on_checkout(INTEGER, INTEGER, INTEGER, INTEGER, TEXT) IS
    'Process an item checkout and update available quantity';

-- Function to update available quantity when item is returned
CREATE OR REPLACE FUNCTION update_inventory_on_return(
    p_item_id INTEGER,
    p_quantity INTEGER,
    p_user_id INTEGER,
    p_community_id INTEGER,
    p_notes TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    new_available_quantity INTEGER,
    message TEXT
) AS $$
DECLARE
    v_total_quantity INTEGER;
    v_available_quantity INTEGER;
BEGIN
    -- Get current quantities
    SELECT quantity, available_quantity INTO v_total_quantity, v_available_quantity
    FROM inventory_items
    WHERE id = p_item_id AND community_id = p_community_id AND deleted_at IS NULL;

    -- Check if item exists
    IF v_total_quantity IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, 'Item not found or community mismatch'::TEXT;
        RETURN;
    END IF;

    -- Ensure available quantity doesn't exceed total
    IF (v_available_quantity + p_quantity) > v_total_quantity THEN
        RETURN QUERY SELECT FALSE, v_available_quantity::INTEGER, 'Return quantity exceeds total inventory'::TEXT;
        RETURN;
    END IF;

    -- Update available quantity
    UPDATE inventory_items
    SET available_quantity = available_quantity + p_quantity,
        updated_at = NOW()
    WHERE id = p_item_id
    RETURNING available_quantity INTO v_available_quantity;

    -- Create audit log entry
    INSERT INTO inventory_log (item_id, user_id, community_id, action, quantity_change, details)
    VALUES (p_item_id, p_user_id, p_community_id, 'return', p_quantity,
            jsonb_build_object('quantity', p_quantity, 'notes', p_notes));

    RETURN QUERY SELECT TRUE, v_available_quantity::INTEGER, 'Return successful'::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_inventory_on_return(INTEGER, INTEGER, INTEGER, INTEGER, TEXT) IS
    'Process an item return and update available quantity';

-- Function to add stock to inventory
CREATE OR REPLACE FUNCTION add_inventory_stock(
    p_item_id INTEGER,
    p_quantity INTEGER,
    p_user_id INTEGER,
    p_community_id INTEGER,
    p_reason TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    new_total_quantity INTEGER,
    new_available_quantity INTEGER,
    message TEXT
) AS $$
DECLARE
    v_new_total INTEGER;
    v_new_available INTEGER;
BEGIN
    -- Validate quantity
    IF p_quantity <= 0 THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'Quantity must be positive'::TEXT;
        RETURN;
    END IF;

    -- Update quantities
    UPDATE inventory_items
    SET quantity = quantity + p_quantity,
        available_quantity = available_quantity + p_quantity,
        updated_at = NOW()
    WHERE id = p_item_id AND community_id = p_community_id AND deleted_at IS NULL
    RETURNING quantity, available_quantity INTO v_new_total, v_new_available;

    -- Check if item was found
    IF v_new_total IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'Item not found or community mismatch'::TEXT;
        RETURN;
    END IF;

    -- Create audit log entry
    INSERT INTO inventory_log (item_id, user_id, community_id, action, quantity_change, details)
    VALUES (p_item_id, p_user_id, p_community_id, 'add_stock', p_quantity,
            jsonb_build_object('quantity', p_quantity, 'reason', p_reason));

    RETURN QUERY SELECT TRUE, v_new_total::INTEGER, v_new_available::INTEGER, 'Stock added successfully'::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION add_inventory_stock(INTEGER, INTEGER, INTEGER, INTEGER, TEXT) IS
    'Add stock to an inventory item and create audit log entry';

-- Function to remove stock from inventory
CREATE OR REPLACE FUNCTION remove_inventory_stock(
    p_item_id INTEGER,
    p_quantity INTEGER,
    p_user_id INTEGER,
    p_community_id INTEGER,
    p_reason TEXT DEFAULT NULL
)
RETURNS TABLE(
    success BOOLEAN,
    new_total_quantity INTEGER,
    new_available_quantity INTEGER,
    message TEXT
) AS $$
DECLARE
    v_current_quantity INTEGER;
    v_current_available INTEGER;
    v_new_total INTEGER;
    v_new_available INTEGER;
BEGIN
    -- Validate quantity
    IF p_quantity <= 0 THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'Quantity must be positive'::TEXT;
        RETURN;
    END IF;

    -- Get current quantities
    SELECT quantity, available_quantity INTO v_current_quantity, v_current_available
    FROM inventory_items
    WHERE id = p_item_id AND community_id = p_community_id AND deleted_at IS NULL;

    -- Check if item exists
    IF v_current_quantity IS NULL THEN
        RETURN QUERY SELECT FALSE, NULL::INTEGER, NULL::INTEGER, 'Item not found or community mismatch'::TEXT;
        RETURN;
    END IF;

    -- Check if sufficient quantity to remove
    IF v_current_quantity < p_quantity THEN
        RETURN QUERY SELECT FALSE, v_current_quantity::INTEGER, v_current_available::INTEGER, 'Cannot remove more than available quantity'::TEXT;
        RETURN;
    END IF;

    -- Update quantities (remove from available first, then total)
    UPDATE inventory_items
    SET quantity = quantity - p_quantity,
        available_quantity = CASE
            WHEN available_quantity >= p_quantity THEN available_quantity - p_quantity
            ELSE 0
        END,
        updated_at = NOW()
    WHERE id = p_item_id
    RETURNING quantity, available_quantity INTO v_new_total, v_new_available;

    -- Create audit log entry
    INSERT INTO inventory_log (item_id, user_id, community_id, action, quantity_change, details)
    VALUES (p_item_id, p_user_id, p_community_id, 'remove_stock', -p_quantity,
            jsonb_build_object('quantity', p_quantity, 'reason', p_reason));

    RETURN QUERY SELECT TRUE, v_new_total::INTEGER, v_new_available::INTEGER, 'Stock removed successfully'::TEXT;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION remove_inventory_stock(INTEGER, INTEGER, INTEGER, INTEGER, TEXT) IS
    'Remove stock from an inventory item and create audit log entry';

-- Function to get inventory summary for a community
CREATE OR REPLACE FUNCTION get_inventory_summary(p_community_id INTEGER)
RETURNS TABLE(
    total_items BIGINT,
    total_quantity BIGINT,
    total_available BIGINT,
    active_checkouts BIGINT,
    overdue_checkouts BIGINT,
    low_stock_items BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(DISTINCT ii.id)::BIGINT,
        COALESCE(SUM(ii.quantity), 0)::BIGINT,
        COALESCE(SUM(ii.available_quantity), 0)::BIGINT,
        COUNT(DISTINCT CASE WHEN ic.status = 'active' THEN ic.id END)::BIGINT,
        COUNT(DISTINCT CASE WHEN ic.status = 'overdue' THEN ic.id END)::BIGINT,
        COUNT(DISTINCT CASE WHEN ii.available_quantity < ii.quantity THEN ii.id END)::BIGINT
    FROM inventory_items ii
    LEFT JOIN inventory_checkouts ic ON ii.id = ic.item_id
    WHERE ii.community_id = p_community_id
      AND ii.deleted_at IS NULL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_inventory_summary(INTEGER) IS
    'Get comprehensive inventory summary for a community';

-- Function to search inventory items
CREATE OR REPLACE FUNCTION search_inventory_items(
    p_community_id INTEGER,
    p_search_query TEXT,
    p_limit INTEGER DEFAULT 20
)
RETURNS TABLE(
    id INTEGER,
    name VARCHAR,
    description TEXT,
    item_type VARCHAR,
    category VARCHAR,
    quantity INTEGER,
    available_quantity INTEGER,
    checkout_price INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        ii.id,
        ii.name,
        ii.description,
        ii.item_type,
        ii.category,
        ii.quantity,
        ii.available_quantity,
        ii.checkout_price
    FROM inventory_items ii
    WHERE ii.community_id = p_community_id
      AND ii.deleted_at IS NULL
      AND to_tsvector('english', ii.name || ' ' || COALESCE(ii.description, '') || ' ' || COALESCE(ii.category, '') || ' ' || COALESCE(ii.item_type, ''))
          @@ plainto_tsquery('english', p_search_query)
    ORDER BY ts_rank(to_tsvector('english', ii.name || ' ' || COALESCE(ii.description, '') || ' ' || COALESCE(ii.category, '') || ' ' || COALESCE(ii.item_type, '')),
             plainto_tsquery('english', p_search_query)) DESC
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_inventory_items(INTEGER, TEXT, INTEGER) IS
    'Full-text search for inventory items in a community';

-- =============================================================================
-- ANALYZE TABLES
-- =============================================================================
ANALYZE inventory_items;
ANALYZE inventory_checkouts;
ANALYZE inventory_log;
