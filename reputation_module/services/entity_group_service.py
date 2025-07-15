"""
Entity group service for managing entity groups
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..models import db

logger = logging.getLogger(__name__)

class EntityGroupService:
    """Service for managing entity groups"""
    
    def __init__(self):
        pass
    
    def create_entity_group(self, name: str, platform: str, server_id: str, 
                           community_id: int, entity_ids: List[str], 
                           created_by: str) -> Dict[str, Any]:
        """Create a new entity group"""
        try:
            # Validate that community exists
            community = db(
                (db.communities.id == community_id) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {"success": False, "error": "Community not found"}
            
            # Check if group with same name already exists in community
            existing_group = db(
                (db.entity_groups.name == name) &
                (db.entity_groups.community_id == community_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if existing_group:
                return {"success": False, "error": "Entity group with this name already exists"}
            
            # Create the entity group
            group_id = db.entity_groups.insert(
                name=name,
                platform=platform,
                server_id=server_id,
                entity_ids=entity_ids,
                community_id=community_id,
                is_active=True,
                created_by=created_by
            )
            
            # Update community's entity_groups list
            current_groups = community.entity_groups or []
            if group_id not in current_groups:
                current_groups.append(group_id)
                db(db.communities.id == community_id).update(
                    entity_groups=current_groups,
                    updated_at=datetime.utcnow()
                )
            
            db.commit()
            
            # Return the created group
            group = db(db.entity_groups.id == group_id).select().first()
            
            return {
                "success": True,
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "platform": group.platform,
                    "server_id": group.server_id,
                    "entity_ids": group.entity_ids,
                    "community_id": group.community_id,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating entity group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_entity_group(self, group_id: int) -> Dict[str, Any]:
        """Get entity group by ID"""
        try:
            group = db(
                (db.entity_groups.id == group_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if not group:
                return {"success": False, "error": "Entity group not found"}
            
            return {
                "success": True,
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "platform": group.platform,
                    "server_id": group.server_id,
                    "entity_ids": group.entity_ids,
                    "community_id": group.community_id,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat(),
                    "updated_at": group.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting entity group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def update_entity_group(self, group_id: int, name: Optional[str] = None,
                           entity_ids: Optional[List[str]] = None,
                           updated_by: str = "system") -> Dict[str, Any]:
        """Update entity group"""
        try:
            group = db(
                (db.entity_groups.id == group_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if not group:
                return {"success": False, "error": "Entity group not found"}
            
            # Prepare update data
            update_data = {
                "updated_at": datetime.utcnow()
            }
            
            if name is not None:
                # Check if new name conflicts with existing groups in same community
                existing_group = db(
                    (db.entity_groups.name == name) &
                    (db.entity_groups.community_id == group.community_id) &
                    (db.entity_groups.id != group_id) &
                    (db.entity_groups.is_active == True)
                ).select().first()
                
                if existing_group:
                    return {"success": False, "error": "Entity group with this name already exists"}
                
                update_data["name"] = name
            
            if entity_ids is not None:
                update_data["entity_ids"] = entity_ids
            
            # Update the group
            db(db.entity_groups.id == group_id).update(**update_data)
            db.commit()
            
            # Return updated group
            updated_group = db(db.entity_groups.id == group_id).select().first()
            
            return {
                "success": True,
                "group": {
                    "id": updated_group.id,
                    "name": updated_group.name,
                    "platform": updated_group.platform,
                    "server_id": updated_group.server_id,
                    "entity_ids": updated_group.entity_ids,
                    "community_id": updated_group.community_id,
                    "created_by": updated_group.created_by,
                    "created_at": updated_group.created_at.isoformat(),
                    "updated_at": updated_group.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error updating entity group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def delete_entity_group(self, group_id: int) -> Dict[str, Any]:
        """Delete (deactivate) entity group"""
        try:
            group = db(
                (db.entity_groups.id == group_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if not group:
                return {"success": False, "error": "Entity group not found"}
            
            # Deactivate the group
            db(db.entity_groups.id == group_id).update(
                is_active=False,
                updated_at=datetime.utcnow()
            )
            
            # Remove from community's entity_groups list
            community = db(db.communities.id == group.community_id).select().first()
            if community and community.entity_groups:
                updated_groups = [g for g in community.entity_groups if g != group_id]
                db(db.communities.id == group.community_id).update(
                    entity_groups=updated_groups,
                    updated_at=datetime.utcnow()
                )
            
            db.commit()
            
            return {"success": True, "message": "Entity group deleted successfully"}
            
        except Exception as e:
            logger.error(f"Error deleting entity group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_community_entity_groups(self, community_id: int) -> List[Dict[str, Any]]:
        """Get all entity groups for a community"""
        try:
            groups = db(
                (db.entity_groups.community_id == community_id) &
                (db.entity_groups.is_active == True)
            ).select(orderby=db.entity_groups.name)
            
            group_list = []
            for group in groups:
                group_list.append({
                    "id": group.id,
                    "name": group.name,
                    "platform": group.platform,
                    "server_id": group.server_id,
                    "entity_ids": group.entity_ids,
                    "entity_count": len(group.entity_ids) if group.entity_ids else 0,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat(),
                    "updated_at": group.updated_at.isoformat()
                })
            
            return group_list
            
        except Exception as e:
            logger.error(f"Error getting community entity groups: {str(e)}")
            return []
    
    def get_entity_groups_by_platform(self, platform: str, server_id: str) -> List[Dict[str, Any]]:
        """Get entity groups by platform and server"""
        try:
            groups = db(
                (db.entity_groups.platform == platform) &
                (db.entity_groups.server_id == server_id) &
                (db.entity_groups.is_active == True)
            ).select(orderby=db.entity_groups.name)
            
            group_list = []
            for group in groups:
                group_list.append({
                    "id": group.id,
                    "name": group.name,
                    "platform": group.platform,
                    "server_id": group.server_id,
                    "entity_ids": group.entity_ids,
                    "entity_count": len(group.entity_ids) if group.entity_ids else 0,
                    "community_id": group.community_id,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat()
                })
            
            return group_list
            
        except Exception as e:
            logger.error(f"Error getting entity groups by platform: {str(e)}")
            return []
    
    def find_entity_groups_for_entity(self, entity_id: str) -> List[Dict[str, Any]]:
        """Find all entity groups that contain a specific entity"""
        try:
            groups = db(
                (db.entity_groups.entity_ids.contains(entity_id)) &
                (db.entity_groups.is_active == True)
            ).select()
            
            group_list = []
            for group in groups:
                group_list.append({
                    "id": group.id,
                    "name": group.name,
                    "platform": group.platform,
                    "server_id": group.server_id,
                    "community_id": group.community_id,
                    "created_by": group.created_by,
                    "created_at": group.created_at.isoformat()
                })
            
            return group_list
            
        except Exception as e:
            logger.error(f"Error finding entity groups for entity: {str(e)}")
            return []
    
    def add_entity_to_group(self, group_id: int, entity_id: str) -> Dict[str, Any]:
        """Add an entity to an entity group"""
        try:
            group = db(
                (db.entity_groups.id == group_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if not group:
                return {"success": False, "error": "Entity group not found"}
            
            entity_ids = group.entity_ids or []
            
            if entity_id not in entity_ids:
                entity_ids.append(entity_id)
                db(db.entity_groups.id == group_id).update(
                    entity_ids=entity_ids,
                    updated_at=datetime.utcnow()
                )
                db.commit()
            
            return {"success": True, "message": f"Entity {entity_id} added to group {group.name}"}
            
        except Exception as e:
            logger.error(f"Error adding entity to group: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def remove_entity_from_group(self, group_id: int, entity_id: str) -> Dict[str, Any]:
        """Remove an entity from an entity group"""
        try:
            group = db(
                (db.entity_groups.id == group_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if not group:
                return {"success": False, "error": "Entity group not found"}
            
            entity_ids = group.entity_ids or []
            
            if entity_id in entity_ids:
                entity_ids.remove(entity_id)
                db(db.entity_groups.id == group_id).update(
                    entity_ids=entity_ids,
                    updated_at=datetime.utcnow()
                )
                db.commit()
            
            return {"success": True, "message": f"Entity {entity_id} removed from group {group.name}"}
            
        except Exception as e:
            logger.error(f"Error removing entity from group: {str(e)}")
            return {"success": False, "error": str(e)}