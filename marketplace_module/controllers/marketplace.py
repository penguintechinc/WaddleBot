"""
Marketplace controller for browsing and managing community modules
"""

import json
import logging
from datetime import datetime, timedelta
from py4web import action, request, response, HTTP, redirect, Field
from py4web.utils.form import Form

from ..models import db
from ..services.module_manager import module_manager
from ..services.router_sync import router_sync

logger = logging.getLogger(__name__)

@action("marketplace")
@action("marketplace/")
def marketplace_home():
    """Marketplace home page with featured modules"""
    try:
        # Get featured modules
        featured_modules = db(
            (db.marketplace_modules.is_featured == True) &
            (db.marketplace_modules.is_active == True)
        ).select(
            orderby=~db.marketplace_modules.rating_average,
            limitby=(0, 6)
        )
        
        # Get popular modules
        popular_modules = db(
            db.marketplace_modules.is_active == True
        ).select(
            orderby=~db.marketplace_modules.download_count,
            limitby=(0, 8)
        )
        
        # Get recent modules
        recent_modules = db(
            db.marketplace_modules.is_active == True
        ).select(
            orderby=~db.marketplace_modules.published_at,
            limitby=(0, 8)
        )
        
        # Get categories
        categories = db(
            db.module_categories.is_active == True
        ).select(
            orderby=db.module_categories.sort_order
        )
        
        return {
            "featured_modules": [dict(module) for module in featured_modules],
            "popular_modules": [dict(module) for module in popular_modules],
            "recent_modules": [dict(module) for module in recent_modules],
            "categories": [dict(cat) for cat in categories]
        }
        
    except Exception as e:
        logger.error(f"Error loading marketplace home: {str(e)}")
        raise HTTP(500, f"Error loading marketplace: {str(e)}")

@action("marketplace/browse")
def browse_modules():
    """Browse modules with filters and search"""
    try:
        # Get query parameters
        category = request.query.get("category")
        search = request.query.get("search", "").strip()
        sort = request.query.get("sort", "popular")  # popular, recent, rating, name
        page = int(request.query.get("page", "1"))
        per_page = min(int(request.query.get("per_page", "20")), 50)
        
        # Build query
        query = (db.marketplace_modules.is_active == True)
        
        if category:
            query &= (db.marketplace_modules.category == category)
        
        if search:
            search_terms = search.lower().split()
            for term in search_terms:
                query &= (
                    db.marketplace_modules.name.lower().like(f"%{term}%") |
                    db.marketplace_modules.display_name.lower().like(f"%{term}%") |
                    db.marketplace_modules.description.lower().like(f"%{term}%") |
                    db.marketplace_modules.tags.contains(term)
                )
        
        # Determine sort order
        if sort == "recent":
            orderby = ~db.marketplace_modules.published_at
        elif sort == "rating":
            orderby = ~db.marketplace_modules.rating_average
        elif sort == "name":
            orderby = db.marketplace_modules.display_name
        else:  # popular
            orderby = ~db.marketplace_modules.download_count
        
        # Get total count
        total_count = db(query).count()
        
        # Get paginated results
        offset = (page - 1) * per_page
        modules = db(query).select(
            orderby=orderby,
            limitby=(offset, offset + per_page)
        )
        
        # Calculate pagination info
        total_pages = (total_count + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages
        
        return {
            "modules": [dict(module) for module in modules],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next
            },
            "filters": {
                "category": category,
                "search": search,
                "sort": sort
            }
        }
        
    except Exception as e:
        logger.error(f"Error browsing modules: {str(e)}")
        raise HTTP(500, f"Error browsing modules: {str(e)}")

@action("marketplace/module/<module_id>")
def module_details(module_id):
    """Get detailed information about a specific module"""
    try:
        # Get module
        module = db(
            (db.marketplace_modules.module_id == module_id) &
            (db.marketplace_modules.is_active == True)
        ).select().first()
        
        if not module:
            raise HTTP(404, "Module not found")
        
        # Get module versions
        versions = db(
            db.module_versions.module_id == module.id
        ).select(
            orderby=~db.module_versions.created_at
        )
        
        # Get module commands
        commands = db(
            db.module_commands.module_id == module.id
        ).select()
        
        # Get recent reviews
        reviews = db(
            db.module_reviews.module_id == module.id
        ).select(
            orderby=~db.module_reviews.created_at,
            limitby=(0, 10)
        )
        
        # Get installation count
        installation_count = db(
            db.module_installations.module_id == module.id
        ).count()
        
        return {
            "module": dict(module),
            "versions": [dict(version) for version in versions],
            "commands": [dict(cmd) for cmd in commands],
            "reviews": [dict(review) for review in reviews],
            "installation_count": installation_count
        }
        
    except Exception as e:
        logger.error(f"Error getting module details for {module_id}: {str(e)}")
        raise HTTP(500, f"Error getting module details: {str(e)}")

@action("marketplace/install", method=["POST"])
def install_module():
    """Install a module for an entity"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        module_id = data.get("module_id")
        entity_id = data.get("entity_id")
        user_id = data.get("user_id")
        version = data.get("version", "latest")
        
        if not all([module_id, entity_id, user_id]):
            raise HTTP(400, "Missing required fields: module_id, entity_id, user_id")
        
        # Check if user has permission to install modules for this entity
        if not module_manager.check_install_permission(entity_id, user_id):
            raise HTTP(403, "Insufficient permissions to install modules")
        
        # Install the module
        result = await module_manager.install_module(module_id, entity_id, user_id, version)
        
        if result["success"]:
            # Sync with router
            await router_sync.sync_module_commands(module_id, entity_id)
            
            return {
                "success": True,
                "message": "Module installed successfully",
                "installation_id": result["installation_id"]
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
        
    except Exception as e:
        logger.error(f"Error installing module: {str(e)}")
        raise HTTP(500, f"Error installing module: {str(e)}")

@action("marketplace/uninstall", method=["POST"])
def uninstall_module():
    """Uninstall a module from an entity"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        module_id = data.get("module_id")
        entity_id = data.get("entity_id")
        user_id = data.get("user_id")
        
        if not all([module_id, entity_id, user_id]):
            raise HTTP(400, "Missing required fields: module_id, entity_id, user_id")
        
        # Check if user has permission
        if not module_manager.check_install_permission(entity_id, user_id):
            raise HTTP(403, "Insufficient permissions to uninstall modules")
        
        # Uninstall the module
        result = await module_manager.uninstall_module(module_id, entity_id, user_id)
        
        if result["success"]:
            # Remove from router
            await router_sync.remove_module_commands(module_id, entity_id)
            
            return {
                "success": True,
                "message": "Module uninstalled successfully"
            }
        else:
            return {
                "success": False,
                "error": result["error"]
            }
        
    except Exception as e:
        logger.error(f"Error uninstalling module: {str(e)}")
        raise HTTP(500, f"Error uninstalling module: {str(e)}")

@action("marketplace/entity/<entity_id>/modules")
def list_entity_modules(entity_id):
    """List installed modules for an entity"""
    try:
        # Get entity
        entity = db(db.entities.entity_id == entity_id).select().first()
        if not entity:
            raise HTTP(404, "Entity not found")
        
        # Get installed modules
        installations = db(
            db.module_installations.entity_id == entity_id
        ).select(
            db.module_installations.ALL,
            db.marketplace_modules.ALL,
            left=db.marketplace_modules.on(
                db.marketplace_modules.id == db.module_installations.module_id
            ),
            orderby=db.marketplace_modules.display_name
        )
        
        installed_modules = []
        for installation in installations:
            module_data = dict(installation.marketplace_modules)
            module_data.update({
                "installation": {
                    "version": installation.module_installations.installed_version,
                    "enabled": installation.module_installations.is_enabled,
                    "installed_at": installation.module_installations.installed_at.isoformat(),
                    "usage_count": installation.module_installations.usage_count,
                    "last_used": installation.module_installations.last_used.isoformat() if installation.module_installations.last_used else None
                }
            })
            installed_modules.append(module_data)
        
        return {
            "entity_id": entity_id,
            "modules": installed_modules,
            "total": len(installed_modules)
        }
        
    except Exception as e:
        logger.error(f"Error listing entity modules for {entity_id}: {str(e)}")
        raise HTTP(500, f"Error listing entity modules: {str(e)}")

@action("marketplace/entity/<entity_id>/toggle", method=["POST"])
def toggle_module_status(entity_id):
    """Enable/disable a module for an entity"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        module_id = data.get("module_id")
        enabled = data.get("enabled", True)
        user_id = data.get("user_id")
        
        if not all([module_id, user_id]):
            raise HTTP(400, "Missing required fields: module_id, user_id")
        
        # Check permissions
        if not module_manager.check_install_permission(entity_id, user_id):
            raise HTTP(403, "Insufficient permissions")
        
        # Update installation status
        installation = db(
            (db.module_installations.entity_id == entity_id) &
            (db.module_installations.module_id == module_id)
        ).select().first()
        
        if not installation:
            raise HTTP(404, "Module not installed")
        
        # Update status
        db.module_installations[installation.id] = dict(is_enabled=enabled)
        db.commit()
        
        # Sync with router
        if enabled:
            await router_sync.enable_module_commands(module_id, entity_id)
        else:
            await router_sync.disable_module_commands(module_id, entity_id)
        
        return {
            "success": True,
            "message": f"Module {'enabled' if enabled else 'disabled'} successfully"
        }
        
    except Exception as e:
        logger.error(f"Error toggling module status: {str(e)}")
        raise HTTP(500, f"Error toggling module status: {str(e)}")

@action("marketplace/categories")
def list_categories():
    """List all module categories"""
    try:
        categories = db(
            db.module_categories.is_active == True
        ).select(
            orderby=db.module_categories.sort_order
        )
        
        category_list = []
        for category in categories:
            # Count modules in category
            module_count = db(
                (db.marketplace_modules.category == category.name) &
                (db.marketplace_modules.is_active == True)
            ).count()
            
            category_data = dict(category)
            category_data["module_count"] = module_count
            category_list.append(category_data)
        
        return {
            "categories": category_list
        }
        
    except Exception as e:
        logger.error(f"Error listing categories: {str(e)}")
        raise HTTP(500, f"Error listing categories: {str(e)}")

@action("marketplace/search")
def search_modules():
    """Search modules with autocomplete support"""
    try:
        query = request.query.get("q", "").strip()
        limit = min(int(request.query.get("limit", "10")), 20)
        
        if len(query) < 2:
            return {"suggestions": []}
        
        # Search in module names and descriptions
        modules = db(
            (db.marketplace_modules.is_active == True) &
            (
                db.marketplace_modules.name.like(f"%{query}%") |
                db.marketplace_modules.display_name.like(f"%{query}%") |
                db.marketplace_modules.description.like(f"%{query}%")
            )
        ).select(
            db.marketplace_modules.module_id,
            db.marketplace_modules.display_name,
            db.marketplace_modules.description,
            db.marketplace_modules.rating_average,
            orderby=~db.marketplace_modules.download_count,
            limitby=(0, limit)
        )
        
        suggestions = []
        for module in modules:
            suggestions.append({
                "module_id": module.module_id,
                "name": module.display_name,
                "description": module.description[:100] + "..." if len(module.description) > 100 else module.description,
                "rating": module.rating_average
            })
        
        return {"suggestions": suggestions}
        
    except Exception as e:
        logger.error(f"Error searching modules: {str(e)}")
        raise HTTP(500, f"Error searching modules: {str(e)}")