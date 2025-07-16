"""
Database models for Inventory Interaction Module
"""

from py4web import DAL, Field
from pydal.validators import IS_NOT_EMPTY, IS_LENGTH, IS_IN_SET, IS_DATETIME
from datetime import datetime, timezone
import os

# Database configuration
DB_URI = os.environ.get("DATABASE_URL", "sqlite://storage.db")

# Initialize database
db = DAL(DB_URI, pool_size=10, migrate=True, fake_migrate=False)

# Define tables
def define_tables(db):
    """Define all database tables for inventory management"""
    
    # Main inventory items table
    db.define_table(
        'inventory_items',
        Field('community_id', 'string', length=255, notnull=True,
              requires=IS_NOT_EMPTY()),
        Field('item_name', 'string', length=255, notnull=True,
              requires=[IS_NOT_EMPTY(), IS_LENGTH(255)]),
        Field('description', 'text'),
        Field('labels', 'json'),  # Store labels as JSON array
        Field('is_checked_out', 'boolean', default=False),
        Field('checked_out_to', 'string', length=255),
        Field('checked_out_at', 'datetime'),
        Field('checked_in_at', 'datetime'),
        Field('created_by', 'string', length=255, notnull=True,
              requires=IS_NOT_EMPTY()),
        Field('created_at', 'datetime', default=datetime.now(timezone.utc)),
        Field('updated_at', 'datetime', default=datetime.now(timezone.utc)),
        migrate=True
    )
    
    # Inventory activity log for audit trail
    db.define_table(
        'inventory_activity',
        Field('community_id', 'string', length=255, notnull=True,
              requires=IS_NOT_EMPTY()),
        Field('item_id', 'reference inventory_items', notnull=True),
        Field('action', 'string', length=100, notnull=True,
              requires=[IS_NOT_EMPTY(), IS_IN_SET(['add', 'checkout', 'checkin', 
                                                   'delete', 'update', 'label_add', 
                                                   'label_remove'])]),
        Field('performed_by', 'string', length=255, notnull=True,
              requires=IS_NOT_EMPTY()),
        Field('details', 'json'),  # Store additional details as JSON
        Field('created_at', 'datetime', default=datetime.now(timezone.utc)),
        migrate=True
    )
    
    # Inventory statistics cache (for performance)
    db.define_table(
        'inventory_stats_cache',
        Field('community_id', 'string', length=255, notnull=True,
              requires=IS_NOT_EMPTY()),
        Field('stats_data', 'json'),
        Field('cached_at', 'datetime', default=datetime.now(timezone.utc)),
        migrate=True
    )
    
    # Create indexes for better performance
    try:
        db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_community ON inventory_items(community_id);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_name ON inventory_items(community_id, item_name);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_checkout ON inventory_items(community_id, is_checked_out);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_created ON inventory_items(community_id, created_at);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_updated ON inventory_items(community_id, updated_at);')
        
        db.executesql('CREATE INDEX IF NOT EXISTS idx_activity_community ON inventory_activity(community_id);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_activity_item ON inventory_activity(item_id);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_activity_action ON inventory_activity(community_id, action);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_activity_created ON inventory_activity(community_id, created_at);')
        
        db.executesql('CREATE INDEX IF NOT EXISTS idx_stats_community ON inventory_stats_cache(community_id);')
        db.executesql('CREATE INDEX IF NOT EXISTS idx_stats_cached ON inventory_stats_cache(community_id, cached_at);')
        
        # Create unique constraint on community_id + item_name
        db.executesql('CREATE UNIQUE INDEX IF NOT EXISTS idx_inventory_unique_name ON inventory_items(community_id, item_name);')
        
    except Exception as e:
        # Some databases might not support IF NOT EXISTS
        pass
    
    return db

# Initialize tables
db = define_tables(db)

# Table references for easy access
inventory_items = db.inventory_items
inventory_activity = db.inventory_activity
inventory_stats_cache = db.inventory_stats_cache