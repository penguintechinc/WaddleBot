"""
RBAC (Role-Based Access Control) service for managing user roles and permissions
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..models import db, GLOBAL_COMMUNITY_ID

logger = logging.getLogger(__name__)

class RBACService:
    """Service for managing role-based access control"""
    
    def __init__(self):
        self.role_hierarchy = {
            'user': 1,
            'moderator': 2,
            'owner': 3
        }
        
        # Thread pool for concurrent operations
        self.max_workers = 10
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # Default permissions for each role
        self.default_permissions = {
            'user': [
                'chat.send',
                'commands.basic',
                'reputation.view'
            ],
            'moderator': [
                'chat.send',
                'commands.basic',
                'commands.moderate',
                'reputation.view',
                'users.timeout',
                'users.kick',
                'users.warn',
                'community.add_user',
                'community.add_entity'
            ],
            'owner': [
                'chat.send',
                'commands.basic',
                'commands.moderate',
                'commands.admin',
                'reputation.view',
                'reputation.manage',
                'users.timeout',
                'users.kick',
                'users.warn',
                'users.ban',
                'community.add_user',
                'community.add_entity',
                'community.remove_user',
                'community.manage_roles',
                'community.manage_settings',
                'community.install_modules',
                'community.delete'
            ]
        }
    
    def initialize_global_community(self) -> None:
        """Initialize the global community if it doesn't exist"""
        try:
            # Check if global community exists
            global_community = db(db.communities.id == GLOBAL_COMMUNITY_ID).select().first()
            
            if not global_community:
                # Create global community
                db.communities.insert(
                    id=GLOBAL_COMMUNITY_ID,
                    name="Global Community",
                    owners=["system"],
                    entity_groups=[],
                    member_ids=[],
                    description="Default global community for all WaddleBot users",
                    is_active=True,
                    settings={
                        "auto_join": True,
                        "default_role": "user",
                        "public": True
                    },
                    created_by="system"
                )
                db.commit()
                logger.info("Global community initialized")
            else:
                logger.debug("Global community already exists")
                
        except Exception as e:
            logger.error(f"Error initializing global community: {str(e)}")
            raise

    def initialize_rbac_permissions(self) -> None:
        """Initialize default RBAC permissions"""
        try:
            permissions = [
                # Chat permissions
                {'name': 'chat.send', 'description': 'Send chat messages', 'category': 'chat'},
                {'name': 'chat.delete', 'description': 'Delete chat messages', 'category': 'chat'},
                
                # Command permissions
                {'name': 'commands.basic', 'description': 'Use basic commands', 'category': 'commands'},
                {'name': 'commands.moderate', 'description': 'Use moderation commands', 'category': 'commands'},
                {'name': 'commands.admin', 'description': 'Use admin commands', 'category': 'commands'},
                
                # User management permissions
                {'name': 'users.timeout', 'description': 'Timeout users', 'category': 'moderation'},
                {'name': 'users.kick', 'description': 'Kick users', 'category': 'moderation'},
                {'name': 'users.warn', 'description': 'Warn users', 'category': 'moderation'},
                {'name': 'users.ban', 'description': 'Ban users', 'category': 'moderation'},
                
                # Community management permissions
                {'name': 'community.add_user', 'description': 'Add users to community', 'category': 'community'},
                {'name': 'community.remove_user', 'description': 'Remove users from community', 'category': 'community'},
                {'name': 'community.add_entity', 'description': 'Add entities to community', 'category': 'community'},
                {'name': 'community.manage_roles', 'description': 'Manage user roles', 'category': 'community'},
                {'name': 'community.manage_settings', 'description': 'Manage community settings', 'category': 'community'},
                {'name': 'community.install_modules', 'description': 'Install/uninstall modules', 'category': 'community'},
                {'name': 'community.delete', 'description': 'Delete community', 'category': 'community'},
                
                # Reputation permissions
                {'name': 'reputation.view', 'description': 'View reputation scores', 'category': 'reputation'},
                {'name': 'reputation.manage', 'description': 'Manage reputation settings', 'category': 'reputation'},
            ]
            
            for perm in permissions:
                existing = db(db.rbac_permissions.name == perm['name']).select().first()
                if not existing:
                    db.rbac_permissions.insert(
                        name=perm['name'],
                        description=perm['description'],
                        category=perm['category'],
                        is_active=True
                    )
            
            db.commit()
            logger.info("RBAC permissions initialized")
            
        except Exception as e:
            logger.error(f"Error initializing RBAC permissions: {str(e)}")
            raise
    
    def initialize_rbac_system(self) -> None:
        """Initialize the complete RBAC system"""
        try:
            logger.info("Initializing RBAC system...")
            
            # Initialize global community first
            self.initialize_global_community()
            
            # Initialize RBAC permissions
            self.initialize_rbac_permissions()
            
            logger.info("RBAC system initialization completed")
            
        except Exception as e:
            logger.error(f"Error initializing RBAC system: {str(e)}")
            raise
    
    def get_user_role_in_community(self, user_id: str, community_id: int) -> str:
        """Get user's role in a specific community"""
        try:
            # Check community RBAC table
            rbac_entry = db(
                (db.community_rbac.user_id == user_id) &
                (db.community_rbac.community_id == community_id) &
                (db.community_rbac.is_active == True)
            ).select().first()
            
            if rbac_entry:
                return rbac_entry.role
            
            # Check if user is a member but no role assigned
            membership = db(
                (db.community_memberships.user_id == user_id) &
                (db.community_memberships.community_id == community_id) &
                (db.community_memberships.is_active == True)
            ).select().first()
            
            if membership:
                # Member with no explicit role - default to user
                return 'user'
            
            # For global community, default to user role
            if community_id == GLOBAL_COMMUNITY_ID:
                return 'user'
            
            # Not a member
            return None
            
        except Exception as e:
            logger.error(f"Error getting user role in community: {str(e)}")
            return None
    
    def get_user_role_for_entity(self, user_id: str, entity_id: str) -> str:
        """Get user's role for a specific entity"""
        try:
            # Check entity-specific role first
            entity_role = db(
                (db.entity_roles.user_id == user_id) &
                (db.entity_roles.entity_id == entity_id) &
                (db.entity_roles.is_active == True)
            ).select().first()
            
            if entity_role:
                return entity_role.role
            
            # Fall back to community role
            # Find which community this entity belongs to
            entity_groups = db(
                (db.entity_groups.entity_ids.contains(entity_id)) &
                (db.entity_groups.is_active == True)
            ).select()
            
            for group in entity_groups:
                if group.community_id:
                    community_role = self.get_user_role_in_community(user_id, group.community_id)
                    if community_role:
                        return community_role
            
            # Default to global community role
            return self.get_user_role_in_community(user_id, GLOBAL_COMMUNITY_ID)
            
        except Exception as e:
            logger.error(f"Error getting user role for entity: {str(e)}")
            return 'user'
    
    def has_permission(self, user_id: str, permission: str, entity_id: str = None, 
                      community_id: int = None) -> bool:
        """Check if user has a specific permission"""
        try:
            # Get user's role
            if entity_id:
                user_role = self.get_user_role_for_entity(user_id, entity_id)
            elif community_id:
                user_role = self.get_user_role_in_community(user_id, community_id)
            else:
                user_role = self.get_user_role_in_community(user_id, GLOBAL_COMMUNITY_ID)
            
            if not user_role:
                return False
            
            # Check if role has permission
            return permission in self.default_permissions.get(user_role, [])
            
        except Exception as e:
            logger.error(f"Error checking permission: {str(e)}")
            return False
    
    def has_role_level(self, user_id: str, required_role: str, entity_id: str = None, 
                      community_id: int = None) -> bool:
        """Check if user has required role level or higher"""
        try:
            # Get user's role
            if entity_id:
                user_role = self.get_user_role_for_entity(user_id, entity_id)
            elif community_id:
                user_role = self.get_user_role_in_community(user_id, community_id)
            else:
                user_role = self.get_user_role_in_community(user_id, GLOBAL_COMMUNITY_ID)
            
            if not user_role:
                return False
            
            # Check role hierarchy
            user_level = self.role_hierarchy.get(user_role, 0)
            required_level = self.role_hierarchy.get(required_role, 0)
            
            return user_level >= required_level
            
        except Exception as e:
            logger.error(f"Error checking role level: {str(e)}")
            return False
    
    def assign_role_to_user(self, user_id: str, role: str, assigned_by: str,
                           entity_id: str = None, community_id: int = None) -> Dict[str, Any]:
        """Assign a role to a user"""
        try:
            if role not in self.role_hierarchy:
                return {"success": False, "error": "Invalid role"}
            
            if entity_id:
                # Entity-specific role assignment
                existing_role = db(
                    (db.entity_roles.user_id == user_id) &
                    (db.entity_roles.entity_id == entity_id) &
                    (db.entity_roles.is_active == True)
                ).select().first()
                
                if existing_role:
                    # Update existing role
                    db(db.entity_roles.id == existing_role.id).update(
                        role=role,
                        assigned_by=assigned_by,
                        assigned_at=datetime.utcnow()
                    )
                else:
                    # Create new role
                    db.entity_roles.insert(
                        entity_id=entity_id,
                        user_id=user_id,
                        role=role,
                        assigned_by=assigned_by,
                        assigned_at=datetime.utcnow(),
                        is_active=True
                    )
                
                target = f"entity {entity_id}"
                
            elif community_id:
                # Community role assignment
                existing_rbac = db(
                    (db.community_rbac.user_id == user_id) &
                    (db.community_rbac.community_id == community_id) &
                    (db.community_rbac.is_active == True)
                ).select().first()
                
                if existing_rbac:
                    # Update existing RBAC entry
                    db(db.community_rbac.id == existing_rbac.id).update(
                        role=role,
                        assigned_by=assigned_by,
                        assigned_at=datetime.utcnow()
                    )
                else:
                    # Create new RBAC entry
                    db.community_rbac.insert(
                        community_id=community_id,
                        user_id=user_id,
                        role=role,
                        assigned_by=assigned_by,
                        assigned_at=datetime.utcnow(),
                        is_active=True
                    )
                
                # Ensure user is a member of the community
                existing_membership = db(
                    (db.community_memberships.user_id == user_id) &
                    (db.community_memberships.community_id == community_id) &
                    (db.community_memberships.is_active == True)
                ).select().first()
                
                if not existing_membership:
                    db.community_memberships.insert(
                        community_id=community_id,
                        user_id=user_id,
                        joined_at=datetime.utcnow(),
                        is_active=True
                    )
                
                target = f"community {community_id}"
            else:
                return {"success": False, "error": "Must specify either entity_id or community_id"}
            
            db.commit()
            
            return {
                "success": True,
                "message": f"Role '{role}' assigned to user {user_id} for {target}"
            }
            
        except Exception as e:
            logger.error(f"Error assigning role: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def ensure_user_in_global_community(self, user_id: str) -> None:
        """Ensure user has membership in global community with default role"""
        try:
            # Check membership
            existing_membership = db(
                (db.community_memberships.user_id == user_id) &
                (db.community_memberships.community_id == GLOBAL_COMMUNITY_ID) &
                (db.community_memberships.is_active == True)
            ).select().first()
            
            if not existing_membership:
                db.community_memberships.insert(
                    community_id=GLOBAL_COMMUNITY_ID,
                    user_id=user_id,
                    joined_at=datetime.utcnow(),
                    is_active=True
                )
            
            # Check RBAC entry
            existing_rbac = db(
                (db.community_rbac.user_id == user_id) &
                (db.community_rbac.community_id == GLOBAL_COMMUNITY_ID) &
                (db.community_rbac.is_active == True)
            ).select().first()
            
            if not existing_rbac:
                db.community_rbac.insert(
                    community_id=GLOBAL_COMMUNITY_ID,
                    user_id=user_id,
                    role='user',
                    assigned_by='system',
                    assigned_at=datetime.utcnow(),
                    is_active=True
                )
            
            db.commit()
            logger.info(f"Ensured user {user_id} is in global community with user role")
            
        except Exception as e:
            logger.error(f"Error ensuring user in global community: {str(e)}")
    
    def get_user_permissions(self, user_id: str, entity_id: str = None, 
                           community_id: int = None) -> List[str]:
        """Get all permissions for a user"""
        try:
            # Get user's role
            if entity_id:
                user_role = self.get_user_role_for_entity(user_id, entity_id)
            elif community_id:
                user_role = self.get_user_role_in_community(user_id, community_id)
            else:
                user_role = self.get_user_role_in_community(user_id, GLOBAL_COMMUNITY_ID)
            
            if not user_role:
                return []
            
            return self.default_permissions.get(user_role, [])
            
        except Exception as e:
            logger.error(f"Error getting user permissions: {str(e)}")
            return []
    
    def get_users_with_role(self, role: str, entity_id: str = None, 
                           community_id: int = None) -> List[Dict[str, Any]]:
        """Get all users with a specific role"""
        try:
            users = []
            
            if entity_id:
                # Get users with entity-specific role
                entity_roles = db(
                    (db.entity_roles.entity_id == entity_id) &
                    (db.entity_roles.role == role) &
                    (db.entity_roles.is_active == True)
                ).select()
                
                for er in entity_roles:
                    users.append({
                        "user_id": er.user_id,
                        "role": er.role,
                        "assigned_by": er.assigned_by,
                        "assigned_at": er.assigned_at.isoformat() if er.assigned_at else None,
                        "scope": "entity",
                        "scope_id": entity_id
                    })
            
            elif community_id:
                # Get users with community role from RBAC table
                rbac_entries = db(
                    (db.community_rbac.community_id == community_id) &
                    (db.community_rbac.role == role) &
                    (db.community_rbac.is_active == True)
                ).select()
                
                for rbac_entry in rbac_entries:
                    users.append({
                        "user_id": rbac_entry.user_id,
                        "role": rbac_entry.role,
                        "assigned_by": rbac_entry.assigned_by,
                        "assigned_at": rbac_entry.assigned_at.isoformat() if rbac_entry.assigned_at else None,
                        "scope": "community",
                        "scope_id": community_id
                    })
            
            return users
            
        except Exception as e:
            logger.error(f"Error getting users with role: {str(e)}")
            return []
    
    def check_permissions_bulk(self, user_permissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check permissions for multiple users/entities concurrently"""
        try:
            def check_single_permission(perm_data):
                user_id = perm_data.get('user_id')
                permission = perm_data.get('permission')
                entity_id = perm_data.get('entity_id')
                community_id = perm_data.get('community_id')
                
                has_perm = self.has_permission(user_id, permission, entity_id, community_id)
                return {
                    'user_id': user_id,
                    'permission': permission,
                    'entity_id': entity_id,
                    'community_id': community_id,
                    'has_permission': has_perm
                }
            
            # Process permissions concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(check_single_permission, perm_data) 
                          for perm_data in user_permissions]
                
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error checking individual permission: {str(e)}")
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Error checking permissions bulk: {str(e)}")
            return []
    
    def assign_roles_bulk(self, role_assignments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Assign roles to multiple users concurrently"""
        try:
            def assign_single_role(assignment_data):
                user_id = assignment_data.get('user_id')
                role = assignment_data.get('role')
                assigned_by = assignment_data.get('assigned_by')
                entity_id = assignment_data.get('entity_id')
                community_id = assignment_data.get('community_id')
                
                return self.assign_role_to_user(user_id, role, assigned_by, entity_id, community_id)
            
            # Process role assignments concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(assign_single_role, assignment_data) 
                          for assignment_data in role_assignments]
                
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error assigning individual role: {str(e)}")
                        results.append({"success": False, "error": str(e)})
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Error assigning roles bulk: {str(e)}")
            return []
    
    def ensure_users_in_global_community_bulk(self, user_ids: List[str]) -> Dict[str, Any]:
        """Ensure multiple users have membership in global community concurrently"""
        try:
            def ensure_single_user(user_id):
                try:
                    self.ensure_user_in_global_community(user_id)
                    return {"user_id": user_id, "success": True}
                except Exception as e:
                    logger.error(f"Error ensuring user {user_id} in global community: {str(e)}")
                    return {"user_id": user_id, "success": False, "error": str(e)}
            
            # Process users concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(ensure_single_user, user_id) 
                          for user_id in user_ids]
                
                results = []
                success_count = 0
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                        if result.get('success'):
                            success_count += 1
                    except Exception as e:
                        logger.error(f"Error processing user in bulk operation: {str(e)}")
                        continue
                
                return {
                    "success": True,
                    "total_users": len(user_ids),
                    "successful_users": success_count,
                    "failed_users": len(user_ids) - success_count,
                    "results": results
                }
                
        except Exception as e:
            logger.error(f"Error ensuring users in global community bulk: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_user_roles_bulk(self, user_entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Get roles for multiple users/entities concurrently"""
        try:
            def get_single_user_role(user_entity_data):
                user_id = user_entity_data.get('user_id')
                entity_id = user_entity_data.get('entity_id')
                community_id = user_entity_data.get('community_id')
                
                if entity_id:
                    role = self.get_user_role_for_entity(user_id, entity_id)
                elif community_id:
                    role = self.get_user_role_in_community(user_id, community_id)
                else:
                    role = self.get_user_role_in_community(user_id, GLOBAL_COMMUNITY_ID)
                
                return {
                    'user_id': user_id,
                    'entity_id': entity_id,
                    'community_id': community_id,
                    'role': role
                }
            
            # Process users concurrently
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(get_single_user_role, user_entity_data) 
                          for user_entity_data in user_entities]
                
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        logger.error(f"Error getting individual user role: {str(e)}")
                        continue
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting user roles bulk: {str(e)}")
            return []
    
    def __del__(self):
        """Cleanup thread pool on service destruction"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=True)

# Global RBAC service instance
rbac_service = RBACService()