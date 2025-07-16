#!/usr/bin/env python3
"""
WaddleBot Inventory Interaction Module

This module provides inventory management functionality for communities,
allowing users to track items (IRL or in-game) with labels and checkout status.

Commands:
- !inventory add <item_name> [description] [labels]
- !inventory checkout <item_name> <username>
- !inventory checkin <item_name>
- !inventory delete <item_name>
- !inventory list [filter]
- !inventory search <query>
- !inventory status <item_name>
- !inventory labels <item_name> [add/remove] [label]
"""

import os
import json
import logging
import threading
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

from py4web import action, request, abort, Field, DAL, URL
from py4web.utils.auth import Auth
from py4web.utils.cors import CORS
from py4web.utils.form import Form, FormStyleBulma
from py4web.core import Fixture
from pydal import Field as DALField
from pydal.validators import IS_NOT_EMPTY, IS_LENGTH, IS_IN_SET, IS_DATETIME

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "20"))
CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))
BULK_OPERATION_SIZE = int(os.environ.get("BULK_OPERATION_SIZE", "1000"))
MAX_LABELS_PER_ITEM = int(os.environ.get("MAX_LABELS_PER_ITEM", "5"))

# Database configuration
DB_URI = os.environ.get("DATABASE_URL", "sqlite://storage.db")
db = DAL(DB_URI, pool_size=10, migrate=True, fake_migrate=False)

# Thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Cache for frequently accessed data
cache = {}
cache_lock = threading.RLock()

@dataclass
class InventoryItem:
    """Represents an inventory item with all its properties"""
    id: Optional[int] = None
    community_id: str = ""
    item_name: str = ""
    description: str = ""
    labels: List[str] = field(default_factory=list)
    is_checked_out: bool = False
    checked_out_to: Optional[str] = None
    checked_out_at: Optional[datetime] = None
    checked_in_at: Optional[datetime] = None
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        # Convert datetime objects to ISO strings
        if result['checked_out_at']:
            result['checked_out_at'] = result['checked_out_at'].isoformat()
        if result['checked_in_at']:
            result['checked_in_at'] = result['checked_in_at'].isoformat()
        if result['created_at']:
            result['created_at'] = result['created_at'].isoformat()
        if result['updated_at']:
            result['updated_at'] = result['updated_at'].isoformat()
        return result

@dataclass
class InventoryStats:
    """Statistics for inventory management"""
    total_items: int = 0
    checked_out_items: int = 0
    available_items: int = 0
    total_labels: int = 0
    most_used_labels: List[str] = field(default_factory=list)
    recent_activity: List[Dict[str, Any]] = field(default_factory=list)

# Database table definitions
def define_tables():
    """Define database tables for inventory management"""
    
    # Main inventory items table
    db.define_table(
        'inventory_items',
        DALField('community_id', 'string', length=255, notnull=True),
        DALField('item_name', 'string', length=255, notnull=True),
        DALField('description', 'text'),
        DALField('labels', 'json'),  # Store labels as JSON array
        DALField('is_checked_out', 'boolean', default=False),
        DALField('checked_out_to', 'string', length=255),
        DALField('checked_out_at', 'datetime'),
        DALField('checked_in_at', 'datetime'),
        DALField('created_by', 'string', length=255, notnull=True),
        DALField('created_at', 'datetime', default=datetime.now(timezone.utc)),
        DALField('updated_at', 'datetime', default=datetime.now(timezone.utc)),
        migrate=True
    )
    
    # Inventory activity log for audit trail
    db.define_table(
        'inventory_activity',
        DALField('community_id', 'string', length=255, notnull=True),
        DALField('item_id', 'reference inventory_items', notnull=True),
        DALField('action', 'string', length=100, notnull=True),  # add, checkout, checkin, delete, update
        DALField('performed_by', 'string', length=255, notnull=True),
        DALField('details', 'json'),  # Store additional details as JSON
        DALField('created_at', 'datetime', default=datetime.now(timezone.utc)),
        migrate=True
    )
    
    # Create indexes for better performance
    db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_community ON inventory_items(community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_name ON inventory_items(community_id, item_name);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_inventory_checkout ON inventory_items(community_id, is_checked_out);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_activity_community ON inventory_activity(community_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_activity_item ON inventory_activity(item_id);')

# Initialize database
define_tables()

class InventoryService:
    """Service class for inventory management operations"""
    
    def __init__(self):
        self.db = db
        self.cache = cache
        self.cache_lock = cache_lock
        self.executor = executor
    
    def add_item(self, community_id: str, item_name: str, description: str, 
                 labels: List[str], created_by: str) -> Tuple[bool, str, Optional[InventoryItem]]:
        """Add a new item to the inventory"""
        try:
            # Validate input
            if not item_name.strip():
                return False, "Item name cannot be empty", None
            
            if len(labels) > MAX_LABELS_PER_ITEM:
                return False, f"Maximum {MAX_LABELS_PER_ITEM} labels allowed per item", None
            
            # Check if item already exists
            existing = self.db.inventory_items(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.item_name == item_name.strip())
            )
            
            if existing:
                return False, f"Item '{item_name}' already exists in inventory", None
            
            # Validate labels
            cleaned_labels = [label.strip().lower() for label in labels if label.strip()]
            if len(cleaned_labels) != len(set(cleaned_labels)):
                return False, "Duplicate labels are not allowed", None
            
            # Create new item
            now = datetime.now(timezone.utc)
            item_id = self.db.inventory_items.insert(
                community_id=community_id,
                item_name=item_name.strip(),
                description=description.strip(),
                labels=cleaned_labels,
                is_checked_out=False,
                created_by=created_by,
                created_at=now,
                updated_at=now
            )
            
            # Log activity
            self.log_activity(
                community_id=community_id,
                item_id=item_id,
                action="add",
                performed_by=created_by,
                details={
                    "item_name": item_name.strip(),
                    "description": description.strip(),
                    "labels": cleaned_labels
                }
            )
            
            # Clear cache
            self.clear_cache(community_id)
            
            # Return the created item
            item = self.get_item_by_id(item_id)
            return True, f"Item '{item_name}' added to inventory", item
            
        except Exception as e:
            logger.error(f"Error adding item: {str(e)}")
            return False, f"Error adding item: {str(e)}", None
    
    def checkout_item(self, community_id: str, item_name: str, 
                      checked_out_to: str, performed_by: str) -> Tuple[bool, str, Optional[InventoryItem]]:
        """Check out an item to a user"""
        try:
            # Find item
            item = self.db.inventory_items(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.item_name == item_name.strip())
            )
            
            if not item:
                return False, f"Item '{item_name}' not found in inventory", None
            
            if item.is_checked_out:
                return False, f"Item '{item_name}' is already checked out to {item.checked_out_to}", None
            
            # Check out item
            now = datetime.now(timezone.utc)
            item.update_record(
                is_checked_out=True,
                checked_out_to=checked_out_to.strip(),
                checked_out_at=now,
                updated_at=now
            )
            
            # Log activity
            self.log_activity(
                community_id=community_id,
                item_id=item.id,
                action="checkout",
                performed_by=performed_by,
                details={
                    "item_name": item_name.strip(),
                    "checked_out_to": checked_out_to.strip()
                }
            )
            
            # Clear cache
            self.clear_cache(community_id)
            
            # Return updated item
            updated_item = self.get_item_by_id(item.id)
            return True, f"Item '{item_name}' checked out to {checked_out_to}", updated_item
            
        except Exception as e:
            logger.error(f"Error checking out item: {str(e)}")
            return False, f"Error checking out item: {str(e)}", None
    
    def checkin_item(self, community_id: str, item_name: str, 
                     performed_by: str) -> Tuple[bool, str, Optional[InventoryItem]]:
        """Check in an item"""
        try:
            # Find item
            item = self.db.inventory_items(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.item_name == item_name.strip())
            )
            
            if not item:
                return False, f"Item '{item_name}' not found in inventory", None
            
            if not item.is_checked_out:
                return False, f"Item '{item_name}' is not checked out", None
            
            # Check in item
            now = datetime.now(timezone.utc)
            previous_user = item.checked_out_to
            item.update_record(
                is_checked_out=False,
                checked_out_to=None,
                checked_in_at=now,
                updated_at=now
            )
            
            # Log activity
            self.log_activity(
                community_id=community_id,
                item_id=item.id,
                action="checkin",
                performed_by=performed_by,
                details={
                    "item_name": item_name.strip(),
                    "previous_user": previous_user
                }
            )
            
            # Clear cache
            self.clear_cache(community_id)
            
            # Return updated item
            updated_item = self.get_item_by_id(item.id)
            return True, f"Item '{item_name}' checked in", updated_item
            
        except Exception as e:
            logger.error(f"Error checking in item: {str(e)}")
            return False, f"Error checking in item: {str(e)}", None
    
    def delete_item(self, community_id: str, item_name: str, 
                    performed_by: str) -> Tuple[bool, str]:
        """Delete an item from inventory"""
        try:
            # Find item
            item = self.db.inventory_items(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.item_name == item_name.strip())
            )
            
            if not item:
                return False, f"Item '{item_name}' not found in inventory"
            
            # Log activity before deletion
            self.log_activity(
                community_id=community_id,
                item_id=item.id,
                action="delete",
                performed_by=performed_by,
                details={
                    "item_name": item_name.strip(),
                    "was_checked_out": item.is_checked_out,
                    "checked_out_to": item.checked_out_to
                }
            )
            
            # Delete item
            item.delete_record()
            
            # Clear cache
            self.clear_cache(community_id)
            
            return True, f"Item '{item_name}' deleted from inventory"
            
        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            return False, f"Error deleting item: {str(e)}"
    
    def list_items(self, community_id: str, filter_type: str = "all") -> List[InventoryItem]:
        """List inventory items with optional filtering"""
        try:
            # Build query based on filter
            query = (self.db.inventory_items.community_id == community_id)
            
            if filter_type == "available":
                query &= (self.db.inventory_items.is_checked_out == False)
            elif filter_type == "checked_out":
                query &= (self.db.inventory_items.is_checked_out == True)
            
            # Get items
            items = self.db(query).select(
                orderby=self.db.inventory_items.item_name
            )
            
            # Convert to InventoryItem objects
            result = []
            for item in items:
                inventory_item = InventoryItem(
                    id=item.id,
                    community_id=item.community_id,
                    item_name=item.item_name,
                    description=item.description,
                    labels=item.labels or [],
                    is_checked_out=item.is_checked_out,
                    checked_out_to=item.checked_out_to,
                    checked_out_at=item.checked_out_at,
                    checked_in_at=item.checked_in_at,
                    created_by=item.created_by,
                    created_at=item.created_at,
                    updated_at=item.updated_at
                )
                result.append(inventory_item)
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing items: {str(e)}")
            return []
    
    def search_items(self, community_id: str, query: str) -> List[InventoryItem]:
        """Search inventory items by name, description, or labels"""
        try:
            search_query = query.strip().lower()
            if not search_query:
                return []
            
            # Search in item name and description
            db_query = (self.db.inventory_items.community_id == community_id) & (
                (self.db.inventory_items.item_name.lower().contains(search_query)) |
                (self.db.inventory_items.description.lower().contains(search_query))
            )
            
            items = self.db(db_query).select(
                orderby=self.db.inventory_items.item_name
            )
            
            # Convert to InventoryItem objects and also search in labels
            result = []
            for item in items:
                inventory_item = InventoryItem(
                    id=item.id,
                    community_id=item.community_id,
                    item_name=item.item_name,
                    description=item.description,
                    labels=item.labels or [],
                    is_checked_out=item.is_checked_out,
                    checked_out_to=item.checked_out_to,
                    checked_out_at=item.checked_out_at,
                    checked_in_at=item.checked_in_at,
                    created_by=item.created_by,
                    created_at=item.created_at,
                    updated_at=item.updated_at
                )
                result.append(inventory_item)
            
            # Also search for items with matching labels
            all_items = self.db(self.db.inventory_items.community_id == community_id).select()
            for item in all_items:
                if item.labels:
                    for label in item.labels:
                        if search_query in label.lower():
                            # Check if not already in result
                            if not any(r.id == item.id for r in result):
                                inventory_item = InventoryItem(
                                    id=item.id,
                                    community_id=item.community_id,
                                    item_name=item.item_name,
                                    description=item.description,
                                    labels=item.labels,
                                    is_checked_out=item.is_checked_out,
                                    checked_out_to=item.checked_out_to,
                                    checked_out_at=item.checked_out_at,
                                    checked_in_at=item.checked_in_at,
                                    created_by=item.created_by,
                                    created_at=item.created_at,
                                    updated_at=item.updated_at
                                )
                                result.append(inventory_item)
                            break
            
            return sorted(result, key=lambda x: x.item_name)
            
        except Exception as e:
            logger.error(f"Error searching items: {str(e)}")
            return []
    
    def get_item_status(self, community_id: str, item_name: str) -> Tuple[bool, str, Optional[InventoryItem]]:
        """Get the status of a specific item"""
        try:
            item = self.db.inventory_items(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.item_name == item_name.strip())
            )
            
            if not item:
                return False, f"Item '{item_name}' not found in inventory", None
            
            inventory_item = InventoryItem(
                id=item.id,
                community_id=item.community_id,
                item_name=item.item_name,
                description=item.description,
                labels=item.labels or [],
                is_checked_out=item.is_checked_out,
                checked_out_to=item.checked_out_to,
                checked_out_at=item.checked_out_at,
                checked_in_at=item.checked_in_at,
                created_by=item.created_by,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            
            # Create status message
            if item.is_checked_out:
                status_msg = f"Item '{item_name}' is checked out to {item.checked_out_to}"
                if item.checked_out_at:
                    status_msg += f" since {item.checked_out_at.strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                status_msg = f"Item '{item_name}' is available"
                if item.checked_in_at:
                    status_msg += f" (last checked in at {item.checked_in_at.strftime('%Y-%m-%d %H:%M:%S')})"
            
            return True, status_msg, inventory_item
            
        except Exception as e:
            logger.error(f"Error getting item status: {str(e)}")
            return False, f"Error getting item status: {str(e)}", None
    
    def manage_labels(self, community_id: str, item_name: str, action: str, 
                     label: str, performed_by: str) -> Tuple[bool, str, Optional[InventoryItem]]:
        """Add or remove labels from an item"""
        try:
            # Find item
            item = self.db.inventory_items(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.item_name == item_name.strip())
            )
            
            if not item:
                return False, f"Item '{item_name}' not found in inventory", None
            
            current_labels = item.labels or []
            label = label.strip().lower()
            
            if action == "add":
                if label in current_labels:
                    return False, f"Label '{label}' already exists on item '{item_name}'", None
                
                if len(current_labels) >= MAX_LABELS_PER_ITEM:
                    return False, f"Maximum {MAX_LABELS_PER_ITEM} labels allowed per item", None
                
                current_labels.append(label)
                success_msg = f"Label '{label}' added to item '{item_name}'"
                
            elif action == "remove":
                if label not in current_labels:
                    return False, f"Label '{label}' not found on item '{item_name}'", None
                
                current_labels.remove(label)
                success_msg = f"Label '{label}' removed from item '{item_name}'"
                
            else:
                return False, "Invalid action. Use 'add' or 'remove'", None
            
            # Update item
            now = datetime.now(timezone.utc)
            item.update_record(
                labels=current_labels,
                updated_at=now
            )
            
            # Log activity
            self.log_activity(
                community_id=community_id,
                item_id=item.id,
                action=f"label_{action}",
                performed_by=performed_by,
                details={
                    "item_name": item_name.strip(),
                    "label": label,
                    "current_labels": current_labels
                }
            )
            
            # Clear cache
            self.clear_cache(community_id)
            
            # Return updated item
            updated_item = self.get_item_by_id(item.id)
            return True, success_msg, updated_item
            
        except Exception as e:
            logger.error(f"Error managing labels: {str(e)}")
            return False, f"Error managing labels: {str(e)}", None
    
    def get_item_by_id(self, item_id: int) -> Optional[InventoryItem]:
        """Get an item by its ID"""
        try:
            item = self.db.inventory_items(item_id)
            if not item:
                return None
            
            return InventoryItem(
                id=item.id,
                community_id=item.community_id,
                item_name=item.item_name,
                description=item.description,
                labels=item.labels or [],
                is_checked_out=item.is_checked_out,
                checked_out_to=item.checked_out_to,
                checked_out_at=item.checked_out_at,
                checked_in_at=item.checked_in_at,
                created_by=item.created_by,
                created_at=item.created_at,
                updated_at=item.updated_at
            )
            
        except Exception as e:
            logger.error(f"Error getting item by ID: {str(e)}")
            return None
    
    def get_stats(self, community_id: str) -> InventoryStats:
        """Get inventory statistics for a community"""
        try:
            # Get basic counts
            total_items = self.db(self.db.inventory_items.community_id == community_id).count()
            checked_out_items = self.db(
                (self.db.inventory_items.community_id == community_id) & 
                (self.db.inventory_items.is_checked_out == True)
            ).count()
            available_items = total_items - checked_out_items
            
            # Get label statistics
            items = self.db(self.db.inventory_items.community_id == community_id).select()
            all_labels = []
            for item in items:
                if item.labels:
                    all_labels.extend(item.labels)
            
            # Count label usage
            label_counts = {}
            for label in all_labels:
                label_counts[label] = label_counts.get(label, 0) + 1
            
            # Get most used labels
            most_used_labels = sorted(label_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            most_used_labels = [label for label, count in most_used_labels]
            
            # Get recent activity
            recent_activity = self.db(
                self.db.inventory_activity.community_id == community_id
            ).select(
                orderby=~self.db.inventory_activity.created_at,
                limitby=(0, 10)
            )
            
            recent_activity_list = []
            for activity in recent_activity:
                recent_activity_list.append({
                    "action": activity.action,
                    "performed_by": activity.performed_by,
                    "details": activity.details,
                    "created_at": activity.created_at.isoformat() if activity.created_at else None
                })
            
            return InventoryStats(
                total_items=total_items,
                checked_out_items=checked_out_items,
                available_items=available_items,
                total_labels=len(set(all_labels)),
                most_used_labels=most_used_labels,
                recent_activity=recent_activity_list
            )
            
        except Exception as e:
            logger.error(f"Error getting stats: {str(e)}")
            return InventoryStats()
    
    def log_activity(self, community_id: str, item_id: int, action: str, 
                     performed_by: str, details: Dict[str, Any]):
        """Log an activity for audit trail"""
        try:
            self.db.inventory_activity.insert(
                community_id=community_id,
                item_id=item_id,
                action=action,
                performed_by=performed_by,
                details=details,
                created_at=datetime.now(timezone.utc)
            )
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging activity: {str(e)}")
    
    def clear_cache(self, community_id: str):
        """Clear cache for a specific community"""
        with self.cache_lock:
            keys_to_remove = [key for key in self.cache.keys() if key.startswith(f"inventory_{community_id}_")]
            for key in keys_to_remove:
                del self.cache[key]

# Initialize service
inventory_service = InventoryService()

# API Routes
@action("inventory", method=["GET", "POST"])
@action.uses(db)
def inventory_api():
    """Main inventory API endpoint"""
    try:
        # Get community and user context
        community_id = request.headers.get("X-Community-ID")
        user_id = request.headers.get("X-User-ID")
        
        if not community_id or not user_id:
            return {"success": False, "error": "Missing community or user context"}
        
        if request.method == "GET":
            # Handle GET requests (list, search, status)
            action_type = request.query.get("action", "list")
            
            if action_type == "list":
                filter_type = request.query.get("filter", "all")
                items = inventory_service.list_items(community_id, filter_type)
                return {
                    "success": True,
                    "items": [item.to_dict() for item in items],
                    "count": len(items)
                }
            
            elif action_type == "search":
                query = request.query.get("query", "")
                items = inventory_service.search_items(community_id, query)
                return {
                    "success": True,
                    "items": [item.to_dict() for item in items],
                    "count": len(items),
                    "query": query
                }
            
            elif action_type == "status":
                item_name = request.query.get("item_name", "")
                success, message, item = inventory_service.get_item_status(community_id, item_name)
                return {
                    "success": success,
                    "message": message,
                    "item": item.to_dict() if item else None
                }
            
            elif action_type == "stats":
                stats = inventory_service.get_stats(community_id)
                return {
                    "success": True,
                    "stats": asdict(stats)
                }
            
            else:
                return {"success": False, "error": "Invalid action"}
        
        elif request.method == "POST":
            # Handle POST requests (add, checkout, checkin, delete, labels)
            data = request.json
            action_type = data.get("action")
            
            if action_type == "add":
                item_name = data.get("item_name", "")
                description = data.get("description", "")
                labels = data.get("labels", [])
                
                success, message, item = inventory_service.add_item(
                    community_id, item_name, description, labels, user_id
                )
                
                return {
                    "success": success,
                    "message": message,
                    "item": item.to_dict() if item else None
                }
            
            elif action_type == "checkout":
                item_name = data.get("item_name", "")
                checked_out_to = data.get("checked_out_to", "")
                
                success, message, item = inventory_service.checkout_item(
                    community_id, item_name, checked_out_to, user_id
                )
                
                return {
                    "success": success,
                    "message": message,
                    "item": item.to_dict() if item else None
                }
            
            elif action_type == "checkin":
                item_name = data.get("item_name", "")
                
                success, message, item = inventory_service.checkin_item(
                    community_id, item_name, user_id
                )
                
                return {
                    "success": success,
                    "message": message,
                    "item": item.to_dict() if item else None
                }
            
            elif action_type == "delete":
                item_name = data.get("item_name", "")
                
                success, message = inventory_service.delete_item(
                    community_id, item_name, user_id
                )
                
                return {
                    "success": success,
                    "message": message
                }
            
            elif action_type == "labels":
                item_name = data.get("item_name", "")
                label_action = data.get("label_action", "")  # add or remove
                label = data.get("label", "")
                
                success, message, item = inventory_service.manage_labels(
                    community_id, item_name, label_action, label, user_id
                )
                
                return {
                    "success": success,
                    "message": message,
                    "item": item.to_dict() if item else None
                }
            
            else:
                return {"success": False, "error": "Invalid action"}
        
        else:
            return {"success": False, "error": "Method not allowed"}
    
    except Exception as e:
        logger.error(f"Error in inventory API: {str(e)}")
        return {"success": False, "error": f"Internal server error: {str(e)}"}

@action("health", method="GET")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.executesql("SELECT 1")
        
        # Test service
        test_stats = inventory_service.get_stats("health_check")
        
        return {
            "status": "healthy",
            "service": "inventory_interaction_module",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "cache": "active",
            "thread_pool": "running"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@action("metrics", method="GET")
def metrics():
    """Metrics endpoint for monitoring"""
    try:
        # Get system metrics
        community_id = request.headers.get("X-Community-ID", "system")
        stats = inventory_service.get_stats(community_id)
        
        return {
            "service": "inventory_interaction_module",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": asdict(stats),
            "performance": {
                "thread_pool_size": MAX_WORKERS,
                "cache_ttl": CACHE_TTL,
                "max_labels_per_item": MAX_LABELS_PER_ITEM
            }
        }
    except Exception as e:
        logger.error(f"Metrics failed: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    # Development server
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8024, reload=True)