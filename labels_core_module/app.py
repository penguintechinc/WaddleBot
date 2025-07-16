"""
Labels Core Module for WaddleBot
High-performance multi-threaded module for label management, user verification, and entity group role assignment
Designed to handle thousands of requests per second
"""

from py4web import action, request, response, DAL, Field, HTTP
from py4web.utils.cors import CORS
import json
import os
import logging
import hashlib
import secrets
import threading
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any
import requests
from dataclasses import dataclass, asdict
from collections import defaultdict
import asyncio
from queue import Queue
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection with connection pooling
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

db = DAL(DATABASE_URL, pool_size=50, migrate=True)

# Redis connection for caching
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD")

try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}")
    redis_client = None

# Thread pool for concurrent operations
MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "20"))
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Performance configuration
CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))  # 5 minutes
BULK_OPERATION_SIZE = int(os.environ.get("BULK_OPERATION_SIZE", "1000"))
REQUEST_TIMEOUT = int(os.environ.get("REQUEST_TIMEOUT", "30"))

# Define database tables with proper indexing
db.define_table(
    'labels',
    Field('id', 'id'),
    Field('name', 'string', required=True),
    Field('category', 'string', required=True),  # user, module, community, entityGroup
    Field('description', 'text'),
    Field('color', 'string'),  # Hex color code
    Field('is_system', 'boolean', default=False),  # System-defined labels
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'entity_labels',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),
    Field('entity_type', 'string', required=True),  # user, module, community, entityGroup
    Field('label_id', 'reference labels', required=True),
    Field('applied_by', 'string', required=True),
    Field('applied_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime'),  # Optional expiration
    Field('metadata', 'json'),  # Additional label-specific data
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'user_identities',
    Field('id', 'id'),
    Field('user_id', 'string', required=True),  # WaddleBot user ID
    Field('platform', 'string', required=True),  # twitch, discord, slack
    Field('platform_id', 'string', required=True),  # Platform-specific user ID
    Field('platform_username', 'string', required=True),
    Field('verification_code', 'string'),
    Field('verification_expires', 'datetime'),
    Field('is_verified', 'boolean', default=False),
    Field('verified_at', 'datetime'),
    Field('verification_method', 'string'),  # code, oauth, manual
    Field('metadata', 'json'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'entity_groups',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),  # Community/server ID
    Field('platform', 'string', required=True),  # discord, twitch
    Field('group_type', 'string', required=True),  # role, moderator, vip
    Field('group_id', 'string', required=True),  # Platform-specific group ID
    Field('group_name', 'string', required=True),
    Field('auto_assign_rules', 'json'),  # Label-based assignment rules
    Field('is_auto_assign', 'boolean', default=False),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'entity_group_members',
    Field('id', 'id'),
    Field('entity_group_id', 'reference entity_groups', required=True),
    Field('user_id', 'string', required=True),
    Field('platform_id', 'string', required=True),
    Field('assigned_by', 'string', required=True),
    Field('assigned_reason', 'string'),  # manual, auto_label, auto_rule
    Field('assigned_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime'),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

db.define_table(
    'label_search_cache',
    Field('id', 'id'),
    Field('search_key', 'string', required=True, unique=True),
    Field('entity_type', 'string', required=True),
    Field('results', 'json', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('expires_at', 'datetime', required=True),
    migrate=True
)

# Create comprehensive indexes for performance
try:
    # Label indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_labels_category ON labels(category, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_labels_name ON labels(name, is_active);')
    
    # Entity label indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_labels_entity ON entity_labels(entity_id, entity_type, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_labels_label ON entity_labels(label_id, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_labels_composite ON entity_labels(entity_type, label_id, is_active);')
    
    # User identity indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_user_identities_user ON user_identities(user_id, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_user_identities_platform ON user_identities(platform, platform_id, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_user_identities_verification ON user_identities(verification_code, verification_expires);')
    
    # Entity group indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_groups_entity ON entity_groups(entity_id, platform, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_groups_auto ON entity_groups(is_auto_assign, is_active);')
    
    # Entity group member indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_group_members_group ON entity_group_members(entity_group_id, is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_entity_group_members_user ON entity_group_members(user_id, is_active);')
    
    # Search cache indexes
    db.executesql('CREATE INDEX IF NOT EXISTS idx_label_search_cache_key ON label_search_cache(search_key, expires_at);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_label_search_cache_expire ON label_search_cache(expires_at);')
    
except Exception as e:
    logger.warning(f"Could not create indexes: {e}")

db.commit()

# CORS setup
CORS(response)

# Module configuration
MODULE_NAME = os.environ.get("MODULE_NAME", "labels_core")
MODULE_VERSION = os.environ.get("MODULE_VERSION", "1.0.0")
ROUTER_API_URL = os.environ.get("ROUTER_API_URL", "http://router:8000/router")

# Data classes for type safety
@dataclass
class LabelInfo:
    id: int
    name: str
    category: str
    description: str
    color: str
    is_system: bool
    created_by: str
    created_at: datetime
    is_active: bool

@dataclass
class EntityLabelInfo:
    entity_id: str
    entity_type: str
    label_name: str
    label_color: str
    applied_by: str
    applied_at: datetime
    expires_at: Optional[datetime]
    metadata: Dict

@dataclass
class UserIdentityInfo:
    user_id: str
    platform: str
    platform_id: str
    platform_username: str
    is_verified: bool
    verified_at: Optional[datetime]
    verification_method: str

# Cache management
class CacheManager:
    def __init__(self):
        self.local_cache = {}
        self.cache_timestamps = {}
        self.cache_lock = threading.RLock()
    
    def get(self, key: str) -> Any:
        with self.cache_lock:
            # Try Redis first
            if redis_client:
                try:
                    value = redis_client.get(f"labels:{key}")
                    if value:
                        return json.loads(value)
                except Exception as e:
                    logger.warning(f"Redis get error: {e}")
            
            # Fall back to local cache
            if key in self.local_cache:
                if time.time() - self.cache_timestamps[key] < CACHE_TTL:
                    return self.local_cache[key]
                else:
                    del self.local_cache[key]
                    del self.cache_timestamps[key]
            
            return None
    
    def set(self, key: str, value: Any, ttl: int = CACHE_TTL):
        with self.cache_lock:
            # Set in Redis
            if redis_client:
                try:
                    redis_client.setex(f"labels:{key}", ttl, json.dumps(value))
                except Exception as e:
                    logger.warning(f"Redis set error: {e}")
            
            # Set in local cache
            self.local_cache[key] = value
            self.cache_timestamps[key] = time.time()
    
    def delete(self, key: str):
        with self.cache_lock:
            # Delete from Redis
            if redis_client:
                try:
                    redis_client.delete(f"labels:{key}")
                except Exception as e:
                    logger.warning(f"Redis delete error: {e}")
            
            # Delete from local cache
            if key in self.local_cache:
                del self.local_cache[key]
                del self.cache_timestamps[key]

cache_manager = CacheManager()

# Background task queue for async operations
task_queue = Queue()

def background_worker():
    """Background worker for processing async tasks"""
    while True:
        try:
            task = task_queue.get(timeout=1)
            if task is None:
                break
            
            task_type = task.get('type')
            if task_type == 'auto_assign_roles':
                process_auto_assign_roles(task['data'])
            elif task_type == 'cleanup_expired':
                cleanup_expired_items()
            elif task_type == 'update_search_cache':
                update_search_cache(task['data'])
            
            task_queue.task_done()
        except Exception as e:
            if str(e) != "Empty":  # Ignore timeout exceptions
                logger.error(f"Background worker error: {e}")

# Start background worker thread
worker_thread = threading.Thread(target=background_worker, daemon=True)
worker_thread.start()

@action("health", method=["GET"])
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "performance": {
            "cache_size": len(cache_manager.local_cache),
            "active_threads": threading.active_count(),
            "task_queue_size": task_queue.qsize()
        }
    }

@action("labels", method=["GET"])
def list_labels():
    """List labels with caching and filtering"""
    try:
        category = request.query.get("category")
        entity_id = request.query.get("entity_id")
        is_system = request.query.get("is_system")
        
        cache_key = f"labels:{category}:{entity_id}:{is_system}"
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        # Build query
        query = (db.labels.is_active == True)
        if category:
            query &= (db.labels.category == category)
        if is_system is not None:
            query &= (db.labels.is_system == (is_system.lower() == 'true'))
        
        # Execute query with thread pool
        def fetch_labels():
            labels = db(query).select(
                orderby=db.labels.category | db.labels.name,
                limitby=(0, 1000)  # Limit for performance
            )
            
            label_list = []
            for label in labels:
                label_info = LabelInfo(
                    id=label.id,
                    name=label.name,
                    category=label.category,
                    description=label.description or "",
                    color=label.color or "#000000",
                    is_system=label.is_system,
                    created_by=label.created_by,
                    created_at=label.created_at,
                    is_active=label.is_active
                )
                label_list.append(asdict(label_info))
            
            return label_list
        
        future = executor.submit(fetch_labels)
        labels = future.result(timeout=REQUEST_TIMEOUT)
        
        result = {
            "success": True,
            "labels": labels,
            "total": len(labels)
        }
        
        cache_manager.set(cache_key, result)
        return result
        
    except Exception as e:
        logger.error(f"Error listing labels: {str(e)}")
        return {
            "success": False,
            "error": f"Error listing labels: {str(e)}"
        }

@action("labels", method=["POST"])
def create_label():
    """Create a new label with validation"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        name = data.get("name", "").strip()
        category = data.get("category", "").strip()
        description = data.get("description", "").strip()
        color = data.get("color", "#000000").strip()
        created_by = data.get("created_by", "").strip()
        
        if not all([name, category, created_by]):
            raise HTTP(400, "Missing required fields: name, category, created_by")
        
        if category not in ["user", "module", "community", "entityGroup"]:
            raise HTTP(400, "Invalid category. Must be: user, module, community, entityGroup")
        
        # Check if label already exists
        existing = db(
            (db.labels.name == name) &
            (db.labels.category == category) &
            (db.labels.is_active == True)
        ).select().first()
        
        if existing:
            raise HTTP(409, f"Label '{name}' already exists in category '{category}'")
        
        # Create label
        label_id = db.labels.insert(
            name=name,
            category=category,
            description=description,
            color=color,
            created_by=created_by
        )
        
        db.commit()
        
        # Clear related caches
        cache_manager.delete(f"labels:{category}:None:None")
        cache_manager.delete(f"labels:None:None:None")
        
        return {
            "success": True,
            "message": f"Label '{name}' created successfully",
            "label_id": label_id
        }
        
    except Exception as e:
        logger.error(f"Error creating label: {str(e)}")
        raise HTTP(500, f"Error creating label: {str(e)}")

@action("labels/apply", method=["POST"])
def apply_label():
    """Apply label to entity with bulk operation support"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        # Support both single and bulk operations
        if isinstance(data, list):
            return apply_labels_bulk(data)
        
        entity_id = data.get("entity_id")
        entity_type = data.get("entity_type")
        label_id = data.get("label_id")
        applied_by = data.get("applied_by")
        expires_at = data.get("expires_at")
        metadata = data.get("metadata", {})
        
        if not all([entity_id, entity_type, label_id, applied_by]):
            raise HTTP(400, "Missing required fields")
        
        # Validate entity type
        if entity_type not in ["user", "module", "community", "entityGroup"]:
            raise HTTP(400, "Invalid entity_type")
        
        # Check if label exists
        label = db(db.labels.id == label_id).select().first()
        if not label:
            raise HTTP(404, "Label not found")
        
        # Check if entity_type is a community and validate label limit
        if entity_type == "community":
            current_labels = db(
                (db.entity_labels.entity_id == entity_id) &
                (db.entity_labels.entity_type == entity_type) &
                (db.entity_labels.is_active == True)
            ).count()
            
            if current_labels >= 5:
                raise HTTP(400, "Community can have maximum 5 labels")
        
        # Check if entity_type is a user and validate label limit per community
        if entity_type == "user":
            # Extract community from applied_by or entity context
            community_id = data.get("community_id")
            if community_id:
                current_user_labels = db(
                    (db.entity_labels.entity_id == entity_id) &
                    (db.entity_labels.entity_type == entity_type) &
                    (db.entity_labels.applied_by == applied_by) &
                    (db.entity_labels.is_active == True)
                ).count()
                
                if current_user_labels >= 5:
                    raise HTTP(400, "User can have maximum 5 labels per community")
        
        # Parse expires_at if provided
        expires_datetime = None
        if expires_at:
            try:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTP(400, "Invalid expires_at format")
        
        # Check if label is already applied
        existing = db(
            (db.entity_labels.entity_id == entity_id) &
            (db.entity_labels.entity_type == entity_type) &
            (db.entity_labels.label_id == label_id) &
            (db.entity_labels.is_active == True)
        ).select().first()
        
        if existing:
            raise HTTP(409, "Label already applied to this entity")
        
        # Apply label
        entity_label_id = db.entity_labels.insert(
            entity_id=entity_id,
            entity_type=entity_type,
            label_id=label_id,
            applied_by=applied_by,
            expires_at=expires_datetime,
            metadata=metadata
        )
        
        db.commit()
        
        # Clear related caches
        cache_manager.delete(f"entity_labels:{entity_type}:{entity_id}")
        
        # Trigger auto-role assignment if applicable
        if entity_type == "user":
            task_queue.put({
                'type': 'auto_assign_roles',
                'data': {
                    'user_id': entity_id,
                    'label_id': label_id,
                    'applied_by': applied_by
                }
            })
        
        return {
            "success": True,
            "message": f"Label applied successfully",
            "entity_label_id": entity_label_id
        }
        
    except Exception as e:
        logger.error(f"Error applying label: {str(e)}")
        raise HTTP(500, f"Error applying label: {str(e)}")

def apply_labels_bulk(label_applications: List[Dict]) -> Dict:
    """Apply multiple labels in bulk for performance"""
    try:
        if len(label_applications) > BULK_OPERATION_SIZE:
            raise HTTP(400, f"Bulk operation limited to {BULK_OPERATION_SIZE} items")
        
        results = []
        failed_applications = []
        
        def process_batch(batch):
            batch_results = []
            for app in batch:
                try:
                    # Validate required fields
                    if not all(key in app for key in ["entity_id", "entity_type", "label_id", "applied_by"]):
                        batch_results.append({
                            "success": False,
                            "error": "Missing required fields",
                            "application": app
                        })
                        continue
                    
                    # Check if label exists
                    label = db(db.labels.id == app["label_id"]).select().first()
                    if not label:
                        batch_results.append({
                            "success": False,
                            "error": "Label not found",
                            "application": app
                        })
                        continue
                    
                    # Check if already applied
                    existing = db(
                        (db.entity_labels.entity_id == app["entity_id"]) &
                        (db.entity_labels.entity_type == app["entity_type"]) &
                        (db.entity_labels.label_id == app["label_id"]) &
                        (db.entity_labels.is_active == True)
                    ).select().first()
                    
                    if existing:
                        batch_results.append({
                            "success": False,
                            "error": "Label already applied",
                            "application": app
                        })
                        continue
                    
                    # Apply label
                    entity_label_id = db.entity_labels.insert(
                        entity_id=app["entity_id"],
                        entity_type=app["entity_type"],
                        label_id=app["label_id"],
                        applied_by=app["applied_by"],
                        expires_at=app.get("expires_at"),
                        metadata=app.get("metadata", {})
                    )
                    
                    batch_results.append({
                        "success": True,
                        "entity_label_id": entity_label_id,
                        "application": app
                    })
                    
                except Exception as e:
                    batch_results.append({
                        "success": False,
                        "error": str(e),
                        "application": app
                    })
            
            return batch_results
        
        # Process in batches using thread pool
        batch_size = 100
        futures = []
        
        for i in range(0, len(label_applications), batch_size):
            batch = label_applications[i:i + batch_size]
            future = executor.submit(process_batch, batch)
            futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            batch_results = future.result()
            results.extend(batch_results)
        
        db.commit()
        
        # Count successes and failures
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return {
            "success": True,
            "message": f"Bulk operation completed: {successful} successful, {failed} failed",
            "results": results,
            "summary": {
                "total": len(label_applications),
                "successful": successful,
                "failed": failed
            }
        }
        
    except Exception as e:
        logger.error(f"Error in bulk label application: {str(e)}")
        return {
            "success": False,
            "error": f"Error in bulk label application: {str(e)}"
        }

@action("labels/search", method=["GET"])
def search_by_labels():
    """Search entities by labels with high-performance caching"""
    try:
        entity_type = request.query.get("entity_type", "").strip()
        label_names = request.query.get("labels", "").strip()
        community_id = request.query.get("community_id")
        limit = min(int(request.query.get("limit", "100")), 1000)
        
        if not entity_type or not label_names:
            raise HTTP(400, "Missing required parameters: entity_type, labels")
        
        if entity_type not in ["user", "module", "community", "entityGroup"]:
            raise HTTP(400, "Invalid entity_type")
        
        label_list = [label.strip() for label in label_names.split(",")]
        
        # Create cache key
        cache_key = f"search:{entity_type}:{':'.join(sorted(label_list))}:{community_id}:{limit}"
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            return cached_result
        
        def execute_search():
            # Get label IDs
            label_ids = db(
                (db.labels.name.belongs(label_list)) &
                (db.labels.category == entity_type) &
                (db.labels.is_active == True)
            ).select(db.labels.id)
            
            if not label_ids:
                return []
            
            label_id_list = [label.id for label in label_ids]
            
            # Find entities with these labels
            query = (
                (db.entity_labels.label_id.belongs(label_id_list)) &
                (db.entity_labels.entity_type == entity_type) &
                (db.entity_labels.is_active == True)
            )
            
            # Group by entity to find entities with multiple matching labels
            entity_labels = db(query).select(
                db.entity_labels.entity_id,
                db.entity_labels.label_id,
                db.labels.name,
                db.labels.color,
                left=db.labels.on(db.labels.id == db.entity_labels.label_id)
            )
            
            # Group results by entity
            entity_results = defaultdict(list)
            for el in entity_labels:
                entity_results[el.entity_labels.entity_id].append({
                    "label_id": el.entity_labels.label_id,
                    "label_name": el.labels.name,
                    "label_color": el.labels.color
                })
            
            # Filter entities that have all requested labels if multiple labels specified
            if len(label_list) > 1:
                filtered_results = {}
                for entity_id, labels in entity_results.items():
                    label_names_found = {label["label_name"] for label in labels}
                    if all(label_name in label_names_found for label_name in label_list):
                        filtered_results[entity_id] = labels
                entity_results = filtered_results
            
            # Convert to list and limit results
            results = []
            for entity_id, labels in list(entity_results.items())[:limit]:
                results.append({
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "labels": labels,
                    "match_count": len(labels)
                })
            
            return results
        
        future = executor.submit(execute_search)
        results = future.result(timeout=REQUEST_TIMEOUT)
        
        response_data = {
            "success": True,
            "entity_type": entity_type,
            "searched_labels": label_list,
            "results": results,
            "total": len(results)
        }
        
        cache_manager.set(cache_key, response_data)
        return response_data
        
    except Exception as e:
        logger.error(f"Error searching by labels: {str(e)}")
        return {
            "success": False,
            "error": f"Error searching by labels: {str(e)}"
        }

@action("identity/verify", method=["POST"])
def initiate_verification():
    """Initiate user identity verification"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        user_id = data.get("user_id")
        platform = data.get("platform")
        platform_username = data.get("platform_username")
        
        if not all([user_id, platform, platform_username]):
            raise HTTP(400, "Missing required fields: user_id, platform, platform_username")
        
        if platform not in ["twitch", "discord", "slack"]:
            raise HTTP(400, "Invalid platform")
        
        # Generate verification code
        verification_code = secrets.token_urlsafe(32)
        verification_expires = datetime.utcnow() + timedelta(minutes=30)
        
        # Check if identity already exists
        existing = db(
            (db.user_identities.user_id == user_id) &
            (db.user_identities.platform == platform) &
            (db.user_identities.is_active == True)
        ).select().first()
        
        if existing:
            if existing.is_verified:
                raise HTTP(409, "Identity already verified")
            else:
                # Update existing unverified identity
                db.user_identities[existing.id] = dict(
                    platform_username=platform_username,
                    verification_code=verification_code,
                    verification_expires=verification_expires
                )
        else:
            # Create new identity
            db.user_identities.insert(
                user_id=user_id,
                platform=platform,
                platform_id="",  # Will be set during verification
                platform_username=platform_username,
                verification_code=verification_code,
                verification_expires=verification_expires
            )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Verification initiated for {platform_username} on {platform}",
            "verification_code": verification_code,
            "expires_at": verification_expires.isoformat(),
            "instructions": get_verification_instructions(platform, verification_code)
        }
        
    except Exception as e:
        logger.error(f"Error initiating verification: {str(e)}")
        raise HTTP(500, f"Error initiating verification: {str(e)}")

@action("identity/confirm", method=["POST"])
def confirm_verification():
    """Confirm user identity verification"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        verification_code = data.get("verification_code")
        platform_id = data.get("platform_id")
        
        if not all([verification_code, platform_id]):
            raise HTTP(400, "Missing required fields: verification_code, platform_id")
        
        # Find pending verification
        identity = db(
            (db.user_identities.verification_code == verification_code) &
            (db.user_identities.verification_expires > datetime.utcnow()) &
            (db.user_identities.is_verified == False) &
            (db.user_identities.is_active == True)
        ).select().first()
        
        if not identity:
            raise HTTP(404, "Invalid or expired verification code")
        
        # Update identity as verified
        db.user_identities[identity.id] = dict(
            platform_id=platform_id,
            is_verified=True,
            verified_at=datetime.utcnow(),
            verification_method="code",
            verification_code=None,
            verification_expires=None
        )
        
        db.commit()
        
        # Clear related caches
        cache_manager.delete(f"user_identity:{identity.user_id}")
        
        return {
            "success": True,
            "message": f"Identity verified successfully for {identity.platform_username} on {identity.platform}",
            "user_id": identity.user_id,
            "platform": identity.platform,
            "platform_id": platform_id
        }
        
    except Exception as e:
        logger.error(f"Error confirming verification: {str(e)}")
        raise HTTP(500, f"Error confirming verification: {str(e)}")

@action("entitygroups/assign", method=["POST"])
def assign_entity_group():
    """Assign user to entity group with auto-role support"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        # Support bulk operations
        if isinstance(data, list):
            return assign_entity_groups_bulk(data)
        
        entity_group_id = data.get("entity_group_id")
        user_id = data.get("user_id")
        platform_id = data.get("platform_id")
        assigned_by = data.get("assigned_by")
        assigned_reason = data.get("assigned_reason", "manual")
        expires_at = data.get("expires_at")
        
        if not all([entity_group_id, user_id, platform_id, assigned_by]):
            raise HTTP(400, "Missing required fields")
        
        # Check if entity group exists
        entity_group = db(db.entity_groups.id == entity_group_id).select().first()
        if not entity_group:
            raise HTTP(404, "Entity group not found")
        
        # Check if user is already in group
        existing = db(
            (db.entity_group_members.entity_group_id == entity_group_id) &
            (db.entity_group_members.user_id == user_id) &
            (db.entity_group_members.is_active == True)
        ).select().first()
        
        if existing:
            raise HTTP(409, "User already in entity group")
        
        # Parse expires_at if provided
        expires_datetime = None
        if expires_at:
            try:
                expires_datetime = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            except ValueError:
                raise HTTP(400, "Invalid expires_at format")
        
        # Add user to group
        member_id = db.entity_group_members.insert(
            entity_group_id=entity_group_id,
            user_id=user_id,
            platform_id=platform_id,
            assigned_by=assigned_by,
            assigned_reason=assigned_reason,
            expires_at=expires_datetime
        )
        
        db.commit()
        
        # Execute platform-specific role assignment
        if entity_group.platform == "discord":
            assign_discord_role(entity_group, user_id, platform_id)
        elif entity_group.platform == "twitch":
            assign_twitch_role(entity_group, user_id, platform_id)
        
        return {
            "success": True,
            "message": "User assigned to entity group successfully",
            "member_id": member_id
        }
        
    except Exception as e:
        logger.error(f"Error assigning entity group: {str(e)}")
        raise HTTP(500, f"Error assigning entity group: {str(e)}")

def assign_entity_groups_bulk(assignments: List[Dict]) -> Dict:
    """Assign multiple users to entity groups in bulk"""
    try:
        if len(assignments) > BULK_OPERATION_SIZE:
            raise HTTP(400, f"Bulk operation limited to {BULK_OPERATION_SIZE} items")
        
        results = []
        
        def process_batch(batch):
            batch_results = []
            for assignment in batch:
                try:
                    # Validate required fields
                    if not all(key in assignment for key in ["entity_group_id", "user_id", "platform_id", "assigned_by"]):
                        batch_results.append({
                            "success": False,
                            "error": "Missing required fields",
                            "assignment": assignment
                        })
                        continue
                    
                    # Check if entity group exists
                    entity_group = db(db.entity_groups.id == assignment["entity_group_id"]).select().first()
                    if not entity_group:
                        batch_results.append({
                            "success": False,
                            "error": "Entity group not found",
                            "assignment": assignment
                        })
                        continue
                    
                    # Check if user is already in group
                    existing = db(
                        (db.entity_group_members.entity_group_id == assignment["entity_group_id"]) &
                        (db.entity_group_members.user_id == assignment["user_id"]) &
                        (db.entity_group_members.is_active == True)
                    ).select().first()
                    
                    if existing:
                        batch_results.append({
                            "success": False,
                            "error": "User already in entity group",
                            "assignment": assignment
                        })
                        continue
                    
                    # Add user to group
                    member_id = db.entity_group_members.insert(
                        entity_group_id=assignment["entity_group_id"],
                        user_id=assignment["user_id"],
                        platform_id=assignment["platform_id"],
                        assigned_by=assignment["assigned_by"],
                        assigned_reason=assignment.get("assigned_reason", "bulk"),
                        expires_at=assignment.get("expires_at")
                    )
                    
                    batch_results.append({
                        "success": True,
                        "member_id": member_id,
                        "assignment": assignment
                    })
                    
                except Exception as e:
                    batch_results.append({
                        "success": False,
                        "error": str(e),
                        "assignment": assignment
                    })
            
            return batch_results
        
        # Process in batches using thread pool
        batch_size = 100
        futures = []
        
        for i in range(0, len(assignments), batch_size):
            batch = assignments[i:i + batch_size]
            future = executor.submit(process_batch, batch)
            futures.append(future)
        
        # Collect results
        for future in as_completed(futures):
            batch_results = future.result()
            results.extend(batch_results)
        
        db.commit()
        
        # Count successes and failures
        successful = sum(1 for r in results if r["success"])
        failed = len(results) - successful
        
        return {
            "success": True,
            "message": f"Bulk assignment completed: {successful} successful, {failed} failed",
            "results": results,
            "summary": {
                "total": len(assignments),
                "successful": successful,
                "failed": failed
            }
        }
        
    except Exception as e:
        logger.error(f"Error in bulk entity group assignment: {str(e)}")
        return {
            "success": False,
            "error": f"Error in bulk entity group assignment: {str(e)}"
        }

def process_auto_assign_roles(data: Dict):
    """Process automatic role assignment based on labels"""
    try:
        user_id = data["user_id"]
        label_id = data["label_id"]
        applied_by = data["applied_by"]
        
        # Get user's verified identities
        identities = db(
            (db.user_identities.user_id == user_id) &
            (db.user_identities.is_verified == True) &
            (db.user_identities.is_active == True)
        ).select()
        
        # Get entity groups with auto-assignment rules
        entity_groups = db(
            (db.entity_groups.is_auto_assign == True) &
            (db.entity_groups.is_active == True)
        ).select()
        
        for entity_group in entity_groups:
            if not entity_group.auto_assign_rules:
                continue
            
            rules = entity_group.auto_assign_rules
            
            # Check if the label matches any auto-assign rule
            for rule in rules:
                if rule.get("label_id") == label_id:
                    # Find matching identity for this platform
                    matching_identity = None
                    for identity in identities:
                        if identity.platform == entity_group.platform:
                            matching_identity = identity
                            break
                    
                    if matching_identity:
                        # Check if user is already in the group
                        existing = db(
                            (db.entity_group_members.entity_group_id == entity_group.id) &
                            (db.entity_group_members.user_id == user_id) &
                            (db.entity_group_members.is_active == True)
                        ).select().first()
                        
                        if not existing:
                            # Add user to group
                            db.entity_group_members.insert(
                                entity_group_id=entity_group.id,
                                user_id=user_id,
                                platform_id=matching_identity.platform_id,
                                assigned_by="system",
                                assigned_reason="auto_label"
                            )
                            
                            # Execute platform-specific role assignment
                            if entity_group.platform == "discord":
                                assign_discord_role(entity_group, user_id, matching_identity.platform_id)
                            elif entity_group.platform == "twitch":
                                assign_twitch_role(entity_group, user_id, matching_identity.platform_id)
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error processing auto-assign roles: {str(e)}")

def assign_discord_role(entity_group, user_id: str, platform_id: str):
    """Assign Discord role to user"""
    try:
        # This would integrate with Discord API
        # For now, we'll log the action
        logger.info(f"Discord role assignment: {entity_group.group_name} to user {platform_id}")
        
        # TODO: Implement actual Discord API integration
        # - Get bot token for the server
        # - Use Discord API to assign role
        # - Handle rate limiting and errors
        
    except Exception as e:
        logger.error(f"Error assigning Discord role: {str(e)}")

def assign_twitch_role(entity_group, user_id: str, platform_id: str):
    """Assign Twitch role to user"""
    try:
        # This would integrate with Twitch API
        # For now, we'll log the action
        logger.info(f"Twitch role assignment: {entity_group.group_name} to user {platform_id}")
        
        # TODO: Implement actual Twitch API integration
        # - Get channel access token
        # - Use Twitch API to assign VIP/mod status
        # - Handle rate limiting and errors
        
    except Exception as e:
        logger.error(f"Error assigning Twitch role: {str(e)}")

def get_verification_instructions(platform: str, verification_code: str) -> str:
    """Get platform-specific verification instructions"""
    instructions = {
        "twitch": f"To verify your Twitch identity, type the following in any chat where WaddleBot is active: !verify {verification_code}",
        "discord": f"To verify your Discord identity, use the /verify command in any server where WaddleBot is active: /verify {verification_code}",
        "slack": f"To verify your Slack identity, use the /verify command in any channel where WaddleBot is active: /verify {verification_code}"
    }
    
    return instructions.get(platform, f"Use verification code: {verification_code}")

def cleanup_expired_items():
    """Clean up expired labels and verifications"""
    try:
        now = datetime.utcnow()
        
        # Remove expired labels
        expired_labels = db(
            (db.entity_labels.expires_at < now) &
            (db.entity_labels.is_active == True)
        ).update(is_active=False)
        
        # Remove expired verifications
        expired_verifications = db(
            (db.user_identities.verification_expires < now) &
            (db.user_identities.is_verified == False)
        ).delete()
        
        # Remove expired entity group memberships
        expired_memberships = db(
            (db.entity_group_members.expires_at < now) &
            (db.entity_group_members.is_active == True)
        ).update(is_active=False)
        
        # Remove expired search cache
        expired_cache = db(
            db.label_search_cache.expires_at < now
        ).delete()
        
        db.commit()
        
        logger.info(f"Cleanup completed: {expired_labels} labels, {expired_verifications} verifications, {expired_memberships} memberships, {expired_cache} cache entries")
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")

def update_search_cache(data: Dict):
    """Update search cache with new results"""
    try:
        search_key = data["search_key"]
        entity_type = data["entity_type"]
        results = data["results"]
        ttl = data.get("ttl", CACHE_TTL)
        
        expires_at = datetime.utcnow() + timedelta(seconds=ttl)
        
        # Update or insert cache entry
        existing = db(
            db.label_search_cache.search_key == search_key
        ).select().first()
        
        if existing:
            db.label_search_cache[existing.id] = dict(
                results=results,
                expires_at=expires_at
            )
        else:
            db.label_search_cache.insert(
                search_key=search_key,
                entity_type=entity_type,
                results=results,
                expires_at=expires_at
            )
        
        db.commit()
        
    except Exception as e:
        logger.error(f"Error updating search cache: {str(e)}")

# Schedule periodic cleanup
def schedule_cleanup():
    """Schedule periodic cleanup of expired items"""
    while True:
        try:
            time.sleep(3600)  # Run every hour
            task_queue.put({'type': 'cleanup_expired', 'data': {}})
        except Exception as e:
            logger.error(f"Error scheduling cleanup: {str(e)}")

cleanup_thread = threading.Thread(target=schedule_cleanup, daemon=True)
cleanup_thread.start()

if __name__ == "__main__":
    from py4web import start
    start(port=8012, host="0.0.0.0")