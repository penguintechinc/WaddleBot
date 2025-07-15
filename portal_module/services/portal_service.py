"""
Portal service for community management
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class PortalService:
    """Service for portal community management"""
    
    def __init__(self, db):
        self.db = db
    
    def get_user_communities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get communities where user is an owner"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
            from router_module.services.rbac_service import rbac_service
            
            # Get all communities
            communities = self.db(
                (self.db.communities.is_active == True)
            ).select()
            
            user_communities = []
            for community in communities:
                # Check if user is owner
                user_role = rbac_service.get_user_role_in_community(user_id, community.id)
                if user_role == 'owner':
                    user_communities.append({
                        "id": community.id,
                        "name": community.name,
                        "description": community.description,
                        "member_count": len(community.member_ids or []),
                        "entity_group_count": len(community.entity_groups or []),
                        "created_at": community.created_at,
                        "settings": community.settings or {}
                    })
            
            return user_communities
            
        except Exception as e:
            logger.error(f"Error getting user communities: {str(e)}")
            return []
    
    def get_community_details(self, community_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed community information"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
            from router_module.services.rbac_service import rbac_service
            
            # Check if user is owner
            user_role = rbac_service.get_user_role_in_community(user_id, community_id)
            if user_role != 'owner':
                return None
            
            # Get community
            community = self.db(
                (self.db.communities.id == community_id) &
                (self.db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return None
            
            return {
                "id": community.id,
                "name": community.name,
                "description": community.description,
                "owners": community.owners or [],
                "member_ids": community.member_ids or [],
                "entity_groups": community.entity_groups or [],
                "settings": community.settings or {},
                "created_by": community.created_by,
                "created_at": community.created_at,
                "updated_at": community.updated_at
            }
            
        except Exception as e:
            logger.error(f"Error getting community details: {str(e)}")
            return None
    
    def get_community_members(self, community_id: int, user_id: str) -> List[Dict[str, Any]]:
        """Get community members with roles and reputation"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
            from router_module.services.rbac_service import rbac_service
            
            # Check if user is owner
            user_role = rbac_service.get_user_role_in_community(user_id, community_id)
            if user_role != 'owner':
                return []
            
            # Get community memberships
            memberships = self.db(
                (self.db.community_memberships.community_id == community_id) &
                (self.db.community_memberships.is_active == True)
            ).select()
            
            members = []
            for membership in memberships:
                member_user_id = membership.user_id
                
                # Get user role
                member_role = rbac_service.get_user_role_in_community(member_user_id, community_id)
                
                # Get user reputation
                reputation = self.db(
                    (self.db.user_reputation.user_id == member_user_id) &
                    (self.db.user_reputation.community_id == community_id)
                ).select().first()
                
                # Get display name from portal users if available
                portal_user = self.db(
                    self.db.portal_users.user_id == member_user_id
                ).select().first()
                
                members.append({
                    "user_id": member_user_id,
                    "display_name": portal_user.display_name if portal_user else member_user_id,
                    "role": member_role,
                    "reputation": {
                        "current_score": reputation.current_score if reputation else 0,
                        "total_events": reputation.total_events if reputation else 0,
                        "last_activity": reputation.last_activity if reputation else None
                    },
                    "joined_at": membership.joined_at,
                    "invited_by": membership.invited_by
                })
            
            return sorted(members, key=lambda x: x['reputation']['current_score'], reverse=True)
            
        except Exception as e:
            logger.error(f"Error getting community members: {str(e)}")
            return []
    
    def get_community_modules(self, community_id: int, user_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get installed modules for community"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
            from router_module.services.rbac_service import rbac_service
            
            # Check if user is owner
            user_role = rbac_service.get_user_role_in_community(user_id, community_id)
            if user_role != 'owner':
                return {"core": [], "marketplace": []}
            
            # Get community entity groups
            community = self.db(
                (self.db.communities.id == community_id) &
                (self.db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {"core": [], "marketplace": []}
            
            # Get all entity IDs for this community
            entity_ids = []
            for group_id in (community.entity_groups or []):
                entity_group = self.db(
                    (self.db.entity_groups.id == group_id) &
                    (self.db.entity_groups.is_active == True)
                ).select().first()
                
                if entity_group:
                    entity_ids.extend(entity_group.entity_ids or [])
            
            # Get enabled commands/modules for these entities
            core_modules = []
            marketplace_modules = []
            
            if entity_ids:
                # Get all commands enabled for these entities
                commands = self.db(
                    (self.db.command_permissions.entity_id.belongs(entity_ids)) &
                    (self.db.command_permissions.is_enabled == True)
                ).select(
                    self.db.command_permissions.ALL,
                    self.db.commands.ALL,
                    left=[self.db.commands.on(self.db.commands.id == self.db.command_permissions.command_id)]
                )
                
                for row in commands:
                    command = row.commands
                    permission = row.command_permissions
                    
                    if not command:
                        continue
                    
                    module_info = {
                        "id": command.id,
                        "command": command.command,
                        "prefix": command.prefix,
                        "description": command.description,
                        "module_type": command.module_type,
                        "location": command.location,
                        "version": command.version,
                        "is_active": command.is_active,
                        "usage_count": permission.usage_count,
                        "last_used": permission.last_used
                    }
                    
                    if command.module_type == 'local':
                        core_modules.append(module_info)
                    else:
                        marketplace_modules.append(module_info)
            
            return {
                "core": sorted(core_modules, key=lambda x: x['command']),
                "marketplace": sorted(marketplace_modules, key=lambda x: x['command'])
            }
            
        except Exception as e:
            logger.error(f"Error getting community modules: {str(e)}")
            return {"core": [], "marketplace": []}
    
    def get_community_stats(self, community_id: int, user_id: str) -> Optional[Dict[str, Any]]:
        """Get community statistics"""
        try:
            # Import here to avoid circular imports
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
            from router_module.services.rbac_service import rbac_service
            
            # Check if user is owner
            user_role = rbac_service.get_user_role_in_community(user_id, community_id)
            if user_role != 'owner':
                return None
            
            # Get basic community info
            community = self.db(
                (self.db.communities.id == community_id) &
                (self.db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return None
            
            # Count members by role
            role_counts = {"owner": 0, "moderator": 0, "user": 0}
            
            memberships = self.db(
                (self.db.community_memberships.community_id == community_id) &
                (self.db.community_memberships.is_active == True)
            ).select()
            
            for membership in memberships:
                member_role = rbac_service.get_user_role_in_community(membership.user_id, community_id)
                if member_role in role_counts:
                    role_counts[member_role] += 1
            
            # Get total reputation points
            reputation_stats = self.db(
                self.db.user_reputation.community_id == community_id
            ).select(
                self.db.user_reputation.current_score.sum(),
                self.db.user_reputation.total_events.sum()
            ).first()
            
            total_reputation = reputation_stats['SUM(user_reputation.current_score)'] or 0
            total_events = reputation_stats['SUM(user_reputation.total_events)'] or 0
            
            # Get recent activity count (last 7 days)
            recent_activity = self.db(
                (self.db.reputation_events.community_id == community_id) &
                (self.db.reputation_events.processed_at > datetime.utcnow() - timedelta(days=7))
            ).count()
            
            return {
                "community_id": community_id,
                "name": community.name,
                "total_members": len(community.member_ids or []),
                "role_counts": role_counts,
                "total_reputation": total_reputation,
                "total_events": total_events,
                "recent_activity": recent_activity,
                "entity_groups": len(community.entity_groups or []),
                "created_at": community.created_at
            }
            
        except Exception as e:
            logger.error(f"Error getting community stats: {str(e)}")
            return None