"""
Configuration for Inventory Interaction Module
"""

import os
from typing import Dict, Any

class Config:
    """Configuration class for inventory module"""
    
    # Database configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")
    
    # Performance settings
    MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "20"))
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "300"))  # 5 minutes
    BULK_OPERATION_SIZE = int(os.environ.get("BULK_OPERATION_SIZE", "1000"))
    
    # Business rules
    MAX_LABELS_PER_ITEM = int(os.environ.get("MAX_LABELS_PER_ITEM", "5"))
    MAX_ITEM_NAME_LENGTH = int(os.environ.get("MAX_ITEM_NAME_LENGTH", "255"))
    MAX_DESCRIPTION_LENGTH = int(os.environ.get("MAX_DESCRIPTION_LENGTH", "2000"))
    MAX_LABEL_LENGTH = int(os.environ.get("MAX_LABEL_LENGTH", "50"))
    
    # Redis configuration (for caching)
    REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "")
    REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
    
    # API configuration
    API_VERSION = "v1"
    API_PREFIX = f"/api/{API_VERSION}"
    
    # Logging configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Security settings
    RATE_LIMIT_REQUESTS = int(os.environ.get("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))  # seconds
    
    # Module information
    MODULE_NAME = "inventory_interaction_module"
    MODULE_VERSION = "1.0.0"
    MODULE_DESCRIPTION = "Inventory management module for WaddleBot communities"
    
    # Supported commands
    SUPPORTED_COMMANDS = {
        "add": {
            "description": "Add a new item to inventory",
            "usage": "!inventory add <item_name> [description] [labels]",
            "permissions": ["moderator", "admin", "owner"],
            "parameters": {
                "item_name": {"required": True, "type": "string"},
                "description": {"required": False, "type": "string"},
                "labels": {"required": False, "type": "list"}
            }
        },
        "checkout": {
            "description": "Check out an item to a user",
            "usage": "!inventory checkout <item_name> <username>",
            "permissions": ["moderator", "admin", "owner"],
            "parameters": {
                "item_name": {"required": True, "type": "string"},
                "username": {"required": True, "type": "string"}
            }
        },
        "checkin": {
            "description": "Check in an item",
            "usage": "!inventory checkin <item_name>",
            "permissions": ["moderator", "admin", "owner"],
            "parameters": {
                "item_name": {"required": True, "type": "string"}
            }
        },
        "delete": {
            "description": "Delete an item from inventory",
            "usage": "!inventory delete <item_name>",
            "permissions": ["admin", "owner"],
            "parameters": {
                "item_name": {"required": True, "type": "string"}
            }
        },
        "list": {
            "description": "List inventory items",
            "usage": "!inventory list [filter]",
            "permissions": ["member", "moderator", "admin", "owner"],
            "parameters": {
                "filter": {"required": False, "type": "string", "options": ["all", "available", "checked_out"]}
            }
        },
        "search": {
            "description": "Search inventory items",
            "usage": "!inventory search <query>",
            "permissions": ["member", "moderator", "admin", "owner"],
            "parameters": {
                "query": {"required": True, "type": "string"}
            }
        },
        "status": {
            "description": "Get status of a specific item",
            "usage": "!inventory status <item_name>",
            "permissions": ["member", "moderator", "admin", "owner"],
            "parameters": {
                "item_name": {"required": True, "type": "string"}
            }
        },
        "labels": {
            "description": "Manage labels on an item",
            "usage": "!inventory labels <item_name> [add/remove] [label]",
            "permissions": ["moderator", "admin", "owner"],
            "parameters": {
                "item_name": {"required": True, "type": "string"},
                "action": {"required": False, "type": "string", "options": ["add", "remove"]},
                "label": {"required": False, "type": "string"}
            }
        }
    }
    
    # Activity types for audit logging
    ACTIVITY_TYPES = {
        "add": "Item added to inventory",
        "checkout": "Item checked out",
        "checkin": "Item checked in",
        "delete": "Item deleted from inventory",
        "update": "Item updated",
        "label_add": "Label added to item",
        "label_remove": "Label removed from item"
    }
    
    # Default labels that communities can use
    DEFAULT_LABELS = [
        "electronics",
        "gaming",
        "tools",
        "books",
        "clothing",
        "furniture",
        "collectibles",
        "software",
        "hardware",
        "accessories",
        "consumables",
        "valuable",
        "fragile",
        "heavy",
        "portable",
        "rare",
        "common",
        "new",
        "used",
        "maintenance"
    ]
    
    @classmethod
    def get_all_config(cls) -> Dict[str, Any]:
        """Get all configuration as a dictionary"""
        return {
            "database": {
                "url": cls.DATABASE_URL
            },
            "performance": {
                "max_workers": cls.MAX_WORKERS,
                "cache_ttl": cls.CACHE_TTL,
                "bulk_operation_size": cls.BULK_OPERATION_SIZE
            },
            "business_rules": {
                "max_labels_per_item": cls.MAX_LABELS_PER_ITEM,
                "max_item_name_length": cls.MAX_ITEM_NAME_LENGTH,
                "max_description_length": cls.MAX_DESCRIPTION_LENGTH,
                "max_label_length": cls.MAX_LABEL_LENGTH
            },
            "redis": {
                "host": cls.REDIS_HOST,
                "port": cls.REDIS_PORT,
                "password": cls.REDIS_PASSWORD,
                "db": cls.REDIS_DB
            },
            "api": {
                "version": cls.API_VERSION,
                "prefix": cls.API_PREFIX
            },
            "logging": {
                "level": cls.LOG_LEVEL,
                "format": cls.LOG_FORMAT
            },
            "security": {
                "rate_limit_requests": cls.RATE_LIMIT_REQUESTS,
                "rate_limit_window": cls.RATE_LIMIT_WINDOW
            },
            "module": {
                "name": cls.MODULE_NAME,
                "version": cls.MODULE_VERSION,
                "description": cls.MODULE_DESCRIPTION
            },
            "commands": cls.SUPPORTED_COMMANDS,
            "activity_types": cls.ACTIVITY_TYPES,
            "default_labels": cls.DEFAULT_LABELS
        }
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration settings"""
        try:
            # Validate required settings
            if not cls.DATABASE_URL:
                raise ValueError("DATABASE_URL is required")
            
            if cls.MAX_WORKERS <= 0:
                raise ValueError("MAX_WORKERS must be positive")
            
            if cls.CACHE_TTL <= 0:
                raise ValueError("CACHE_TTL must be positive")
            
            if cls.MAX_LABELS_PER_ITEM <= 0:
                raise ValueError("MAX_LABELS_PER_ITEM must be positive")
            
            if cls.MAX_ITEM_NAME_LENGTH <= 0:
                raise ValueError("MAX_ITEM_NAME_LENGTH must be positive")
            
            # Validate Redis configuration
            if cls.REDIS_PORT <= 0 or cls.REDIS_PORT > 65535:
                raise ValueError("REDIS_PORT must be between 1 and 65535")
            
            if cls.REDIS_DB < 0:
                raise ValueError("REDIS_DB must be non-negative")
            
            # Validate rate limiting
            if cls.RATE_LIMIT_REQUESTS <= 0:
                raise ValueError("RATE_LIMIT_REQUESTS must be positive")
            
            if cls.RATE_LIMIT_WINDOW <= 0:
                raise ValueError("RATE_LIMIT_WINDOW must be positive")
            
            return True
            
        except Exception as e:
            print(f"Configuration validation failed: {e}")
            return False

# Create global config instance
config = Config()

# Validate configuration on import
if not config.validate_config():
    raise RuntimeError("Invalid configuration detected")