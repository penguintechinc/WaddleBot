"""
Community service for managing communities and community context
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..models import db, GLOBAL_COMMUNITY_ID

logger = logging.getLogger(__name__)

class CommunityService:
    """Service for managing communities"""
    
    def __init__(self):
        pass
    
    def create_community(self, name: str, created_by: str, description: str = "", 
                        entity_groups: List[int] = None, member_ids: List[str] = None) -> Dict[str, Any]:
        """Create a new community"""
        try:
            # Check if community with same name already exists
            existing_community = db(
                (db.communities.name == name) &
                (db.communities.is_active == True)
            ).select().first()
            
            if existing_community:
                return {"success": False, "error": "Community with this name already exists"}
            
            # Create the community
            community_id = db.communities.insert(
                name=name,
                owners=[created_by],
                entity_groups=entity_groups or [],
                member_ids=member_ids or [],
                description=description,
                is_active=True,
                settings={
                    'is_global': False,
                    'auto_join': False,
                    'public': True,
                    'allow_user_invite': True,
                    'allow_entity_management': True
                },
                created_by=created_by
            )
            
            # Add creator as owner in community_memberships
            db.community_memberships.insert(
                community_id=community_id,
                user_id=created_by,
                role='owner',
                is_active=True
            )
            
            db.commit()
            
            # Return the created community
            community = db(db.communities.id == community_id).select().first()
            
            return {
                "success": True,
                "community": {
                    "id": community.id,
                    "name": community.name,
                    "description": community.description,
                    "owners": community.owners,
                    "entity_groups": community.entity_groups,
                    "member_ids": community.member_ids,
                    "settings": community.settings,
                    "created_by": community.created_by,
                    "created_at": community.created_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error creating community: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_community(self, community_id: int) -> Dict[str, Any]:
        """Get community by ID"""
        try:
            community = db(
                (db.communities.id == community_id) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {"success": False, "error": "Community not found"}
            
            return {
                "success": True,
                "community": {
                    "id": community.id,
                    "name": community.name,
                    "description": community.description,
                    "owners": community.owners,
                    "entity_groups": community.entity_groups,
                    "member_ids": community.member_ids,
                    "settings": community.settings,
                    "created_by": community.created_by,
                    "created_at": community.created_at.isoformat(),
                    "updated_at": community.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting community: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_community_by_name(self, name: str) -> Dict[str, Any]:
        """Get community by name"""
        try:
            community = db(
                (db.communities.name == name) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {"success": False, "error": "Community not found"}
            
            return {
                "success": True,
                "community": {
                    "id": community.id,
                    "name": community.name,
                    "description": community.description,
                    "owners": community.owners,
                    "entity_groups": community.entity_groups,
                    "member_ids": community.member_ids,
                    "settings": community.settings,
                    "created_by": community.created_by,
                    "created_at": community.created_at.isoformat(),
                    "updated_at": community.updated_at.isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting community by name: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_user_communities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all communities a user is a member of"""
        try:
            # Get communities via membership
            memberships = db(
                (db.community_memberships.user_id == user_id) &
                (db.community_memberships.is_active == True)
            ).select()
            
            community_list = []
            added_communities = set()
            
            for membership in memberships:
                community = db(
                    (db.communities.id == membership.community_id) &
                    (db.communities.is_active == True)
                ).select().first()
                
                if community and community.id not in added_communities:
                    community_list.append({
                        "id": community.id,
                        "name": community.name,
                        "description": community.description,
                        "role": membership.role,
                        "joined_at": membership.joined_at.isoformat(),
                        "is_owner": user_id in (community.owners or []),
                        "member_count": len(community.member_ids or []),
                        "entity_group_count": len(community.entity_groups or [])
                    })
                    added_communities.add(community.id)
            
            # Always include global community
            if GLOBAL_COMMUNITY_ID not in added_communities:
                global_community = db(db.communities.id == GLOBAL_COMMUNITY_ID).select().first()
                if global_community:
                    community_list.append({
                        "id": global_community.id,
                        "name": global_community.name,
                        "description": global_community.description,
                        "role": "member",
                        "joined_at": global_community.created_at.isoformat(),
                        "is_owner": False,
                        "member_count": db(db.user_reputation.community_id == GLOBAL_COMMUNITY_ID).count(),
                        "entity_group_count": len(global_community.entity_groups or [])
                    })
            
            return community_list
            
        except Exception as e:
            logger.error(f"Error getting user communities: {str(e)}")
            return []
    
    def add_user_to_community(self, community_id: int, user_id: str, 
                             invited_by: str, role: str = "member") -> Dict[str, Any]:
        """Add a user to a community"""
        try:
            # Check if community exists
            community = db(
                (db.communities.id == community_id) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {"success": False, "error": "Community not found"}
            
            # Check if user is already a member
            existing_membership = db(
                (db.community_memberships.community_id == community_id) &
                (db.community_memberships.user_id == user_id) &
                (db.community_memberships.is_active == True)
            ).select().first()
            
            if existing_membership:
                return {"success": False, "error": "User is already a member of this community"}
            
            # Add membership
            db.community_memberships.insert(
                community_id=community_id,
                user_id=user_id,
                role=role,
                invited_by=invited_by,
                is_active=True
            )
            
            # Update community member_ids
            member_ids = community.member_ids or []
            if user_id not in member_ids:
                member_ids.append(user_id)
                db(db.communities.id == community_id).update(
                    member_ids=member_ids,
                    updated_at=datetime.utcnow()
                )
            
            db.commit()
            
            return {"success": True, "message": f"User {user_id} added to community {community.name}"}
            
        except Exception as e:
            logger.error(f"Error adding user to community: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def remove_user_from_community(self, community_id: int, user_id: str) -> Dict[str, Any]:
        """Remove a user from a community"""
        try:
            # Can't remove from global community
            if community_id == GLOBAL_COMMUNITY_ID:
                return {"success": False, "error": "Cannot remove user from global community"}
            
            # Deactivate membership
            db(
                (db.community_memberships.community_id == community_id) &
                (db.community_memberships.user_id == user_id)
            ).update(is_active=False)
            
            # Update community member_ids
            community = db(db.communities.id == community_id).select().first()
            if community and community.member_ids:
                member_ids = [uid for uid in community.member_ids if uid != user_id]
                db(db.communities.id == community_id).update(
                    member_ids=member_ids,
                    updated_at=datetime.utcnow()
                )
            
            db.commit()
            
            return {"success": True, "message": f"User {user_id} removed from community"}
            
        except Exception as e:
            logger.error(f"Error removing user from community: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def add_entity_to_community(self, community_id: int, entity_id: str, 
                               added_by: str) -> Dict[str, Any]:
        """Add an entity to a community by creating/updating entity group"""
        try:
            # Parse entity_id to get platform and server
            entity_parts = entity_id.split(':')
            if len(entity_parts) < 3:
                return {"success": False, "error": "Invalid entity_id format. Expected: platform:server:channel"}
            
            platform = entity_parts[0]
            server_id = entity_parts[1]
            
            # Skip Twitch as it doesn't have servers
            if platform == 'twitch':
                return {"success": False, "error": "Twitch entities cannot be added to entity groups (no server concept)"}
            
            # Find or create entity group for this platform+server
            entity_group = db(
                (db.entity_groups.platform == platform) &
                (db.entity_groups.server_id == server_id) &
                (db.entity_groups.community_id == community_id) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if not entity_group:
                # Create new entity group
                group_name = f"{platform}:{server_id}"
                group_id = db.entity_groups.insert(
                    name=group_name,
                    platform=platform,
                    server_id=server_id,
                    entity_ids=[entity_id],
                    community_id=community_id,
                    is_active=True,
                    created_by=added_by
                )
                
                # Update community's entity_groups
                community = db(db.communities.id == community_id).select().first()
                entity_groups = community.entity_groups or []
                entity_groups.append(group_id)
                db(db.communities.id == community_id).update(
                    entity_groups=entity_groups,
                    updated_at=datetime.utcnow()
                )
            else:
                # Add to existing entity group
                entity_ids = entity_group.entity_ids or []
                if entity_id not in entity_ids:
                    entity_ids.append(entity_id)
                    db(db.entity_groups.id == entity_group.id).update(
                        entity_ids=entity_ids,
                        updated_at=datetime.utcnow()
                    )
            
            db.commit()
            
            return {"success": True, "message": f"Entity {entity_id} added to community"}
            
        except Exception as e:
            logger.error(f"Error adding entity to community: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def check_user_permission(self, community_id: int, user_id: str, 
                             required_role: str = "member") -> bool:
        """Check if user has required permission in community"""
        try:
            # Global community - only SuperAdmin has access
            if community_id == GLOBAL_COMMUNITY_ID:
                # Check if user is SuperAdmin (system level permission)
                # This would typically be stored in a user permissions table
                # For now, we'll use a simple check
                return user_id == "system" or user_id in ["superadmin", "admin"]
            
            # Check membership
            membership = db(
                (db.community_memberships.community_id == community_id) &
                (db.community_memberships.user_id == user_id) &
                (db.community_memberships.is_active == True)
            ).select().first()
            
            if not membership:
                return False
            
            # Role hierarchy: owner > admin > moderator > member
            role_hierarchy = {
                'member': 0,
                'moderator': 1,
                'admin': 2,
                'owner': 3
            }
            
            user_role_level = role_hierarchy.get(membership.role, 0)
            required_role_level = role_hierarchy.get(required_role, 0)
            
            return user_role_level >= required_role_level
            
        except Exception as e:
            logger.error(f"Error checking user permission: {str(e)}")
            return False
    
    def get_community_members(self, community_id: int) -> List[Dict[str, Any]]:
        """Get all members of a community"""
        try:
            memberships = db(
                (db.community_memberships.community_id == community_id) &
                (db.community_memberships.is_active == True)
            ).select(orderby=db.community_memberships.joined_at)
            
            members = []
            for membership in memberships:
                members.append({
                    "user_id": membership.user_id,
                    "role": membership.role,
                    "joined_at": membership.joined_at.isoformat(),
                    "invited_by": membership.invited_by
                })
            
            return members
            
        except Exception as e:
            logger.error(f"Error getting community members: {str(e)}")
            return []
    
    def set_user_context(self, user_id: str, community_id: int) -> Dict[str, Any]:
        """Set user's current community context"""
        try:
            # Check if user has access to this community
            if not self.check_user_permission(community_id, user_id):
                return {"success": False, "error": "Access denied to this community"}
            
            # This would typically be stored in a session or cache
            # For now, we'll return success with context info
            community = db(
                (db.communities.id == community_id) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {"success": False, "error": "Community not found"}
            
            return {
                "success": True,
                "context": {
                    "user_id": user_id,
                    "community_id": community_id,
                    "community_name": community.name,
                    "set_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error setting user context: {str(e)}")
            return {"success": False, "error": str(e)}