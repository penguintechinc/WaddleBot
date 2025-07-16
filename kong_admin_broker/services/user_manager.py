import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import traceback
import secrets
import string

from models import db
from config import Config
from .kong_client import KongAdminClient

logger = logging.getLogger(__name__)


class SuperAdminUserManager:
    """Service for managing Kong super admin users"""
    
    def __init__(self):
        self.kong_client = KongAdminClient()
    
    def create_super_admin(self, username: str, email: str, full_name: str,
                          created_by: str, permissions: Optional[List[str]] = None,
                          notes: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Kong super admin user"""
        try:
            # Validate input
            if not username or not email:
                raise ValueError("Username and email are required")
            
            # Check if user already exists
            existing_user = db(db.kong_admin_users.username == username).select().first()
            if existing_user:
                raise ValueError(f"User with username '{username}' already exists")
            
            existing_email = db(db.kong_admin_users.email == email).select().first()
            if existing_email:
                raise ValueError(f"User with email '{email}' already exists")
            
            # Set default permissions if not provided
            if permissions is None:
                permissions = Config.DEFAULT_SUPER_ADMIN_PERMISSIONS
            
            # Create Kong consumer
            consumer_tags = ["super-admin", "waddlebot", f"created-by-{created_by}"]
            kong_consumer = self.kong_client.create_consumer(
                username=username,
                custom_id=f"wbot_admin_{username}",
                tags=consumer_tags
            )
            
            # Generate API key
            api_key_data = self.kong_client.create_api_key(
                consumer_username=username,
                tags=["super-admin", "admin-api"]
            )
            
            # Add to super admin ACL group
            self.kong_client.add_consumer_to_acl_group(username, Config.SUPER_ADMIN_GROUP)
            
            # Add to additional admin groups
            admin_groups = ["admins", "services", "api-users"]
            for group in admin_groups:
                try:
                    self.kong_client.add_consumer_to_acl_group(username, group)
                except Exception as e:
                    logger.warning(f"Failed to add {username} to group {group}: {str(e)}")
            
            # Create database record
            user_id = db.kong_admin_users.insert(
                username=username,
                email=email,
                full_name=full_name,
                kong_consumer_id=kong_consumer['id'],
                api_key=api_key_data['key'],
                permissions=permissions,
                groups=admin_groups + [Config.SUPER_ADMIN_GROUP],
                is_active=True,
                is_super_admin=True,
                created_by=created_by,
                notes=notes or f"Super admin user created by {created_by}"
            )
            
            db.commit()
            
            # Log the action
            self._log_audit_action(
                action="create_super_admin",
                resource_type="user",
                resource_id=str(user_id),
                details={
                    "username": username,
                    "email": email,
                    "full_name": full_name,
                    "kong_consumer_id": kong_consumer['id'],
                    "permissions": permissions,
                    "groups": admin_groups + [Config.SUPER_ADMIN_GROUP]
                },
                performed_by=created_by
            )
            
            logger.info(f"Successfully created super admin user: {username}")
            
            return {
                "success": True,
                "user_id": user_id,
                "username": username,
                "email": email,
                "kong_consumer_id": kong_consumer['id'],
                "api_key": api_key_data['key'],
                "permissions": permissions,
                "groups": admin_groups + [Config.SUPER_ADMIN_GROUP],
                "message": f"Super admin user '{username}' created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating super admin {username}: {str(e)}\n{traceback.format_exc()}")
            
            # Cleanup on failure
            try:
                self.kong_client.delete_consumer(username)
            except:
                pass
            
            raise Exception(f"Failed to create super admin user: {str(e)}")
    
    def get_super_admin(self, username: str) -> Optional[Dict[str, Any]]:
        """Get super admin user by username"""
        try:
            user = db(
                (db.kong_admin_users.username == username) &
                (db.kong_admin_users.is_super_admin == True) &
                (db.kong_admin_users.is_active == True)
            ).select().first()
            
            if not user:
                return None
            
            # Get Kong consumer data
            kong_consumer = self.kong_client.get_consumer(username)
            kong_acl_groups = self.kong_client.get_consumer_acl_groups(username)
            
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "kong_consumer_id": user.kong_consumer_id,
                "api_key": user.api_key,
                "permissions": user.permissions,
                "groups": user.groups,
                "is_active": user.is_active,
                "is_super_admin": user.is_super_admin,
                "last_login": user.last_login,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "created_by": user.created_by,
                "notes": user.notes,
                "kong_consumer": kong_consumer,
                "kong_acl_groups": [group['group'] for group in kong_acl_groups]
            }
            
        except Exception as e:
            logger.error(f"Error getting super admin {username}: {str(e)}")
            raise
    
    def list_super_admins(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """List all super admin users"""
        try:
            query = db.kong_admin_users.is_super_admin == True
            
            if not include_inactive:
                query &= db.kong_admin_users.is_active == True
            
            users = db(query).select(orderby=db.kong_admin_users.created_at)
            
            result = []
            for user in users:
                result.append({
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "is_active": user.is_active,
                    "last_login": user.last_login,
                    "created_at": user.created_at,
                    "created_by": user.created_by,
                    "permissions_count": len(user.permissions or []),
                    "groups_count": len(user.groups or [])
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error listing super admins: {str(e)}")
            raise
    
    def update_super_admin(self, username: str, updates: Dict[str, Any],
                          updated_by: str) -> Dict[str, Any]:
        """Update super admin user"""
        try:
            user = db(
                (db.kong_admin_users.username == username) &
                (db.kong_admin_users.is_super_admin == True)
            ).select().first()
            
            if not user:
                raise ValueError(f"Super admin user '{username}' not found")
            
            # Track changes for audit log
            changes = {}
            
            # Update allowed fields
            allowed_fields = ['email', 'full_name', 'permissions', 'is_active', 'notes']
            update_data = {}
            
            for field in allowed_fields:
                if field in updates:
                    old_value = getattr(user, field)
                    new_value = updates[field]
                    
                    if old_value != new_value:
                        changes[field] = {"old": old_value, "new": new_value}
                        update_data[field] = new_value
            
            if update_data:
                update_data['updated_at'] = datetime.utcnow()
                db(db.kong_admin_users.id == user.id).update(**update_data)
                db.commit()
                
                # Log the action
                self._log_audit_action(
                    action="update_super_admin",
                    resource_type="user",
                    resource_id=str(user.id),
                    details={
                        "username": username,
                        "changes": changes
                    },
                    performed_by=updated_by
                )
                
                logger.info(f"Updated super admin user: {username}")
                
                return {
                    "success": True,
                    "username": username,
                    "changes": changes,
                    "message": f"Super admin user '{username}' updated successfully"
                }
            else:
                return {
                    "success": True,
                    "username": username,
                    "changes": {},
                    "message": "No changes to apply"
                }
                
        except Exception as e:
            logger.error(f"Error updating super admin {username}: {str(e)}")
            raise
    
    def deactivate_super_admin(self, username: str, deactivated_by: str,
                              reason: Optional[str] = None) -> Dict[str, Any]:
        """Deactivate super admin user (soft delete)"""
        try:
            user = db(
                (db.kong_admin_users.username == username) &
                (db.kong_admin_users.is_super_admin == True)
            ).select().first()
            
            if not user:
                raise ValueError(f"Super admin user '{username}' not found")
            
            if not user.is_active:
                return {
                    "success": True,
                    "username": username,
                    "message": f"User '{username}' is already inactive"
                }
            
            # Update user status
            db(db.kong_admin_users.id == user.id).update(
                is_active=False,
                updated_at=datetime.utcnow(),
                notes=f"{user.notes or ''}\n\nDeactivated by {deactivated_by} on {datetime.utcnow()}. Reason: {reason or 'Not specified'}"
            )
            
            # Optionally disable Kong consumer (remove from ACL groups but keep consumer)
            try:
                acl_groups = self.kong_client.get_consumer_acl_groups(username)
                for acl in acl_groups:
                    self.kong_client.remove_consumer_from_acl_group(username, acl['id'])
            except Exception as e:
                logger.warning(f"Failed to remove ACL groups for {username}: {str(e)}")
            
            db.commit()
            
            # Log the action
            self._log_audit_action(
                action="deactivate_super_admin",
                resource_type="user",
                resource_id=str(user.id),
                details={
                    "username": username,
                    "reason": reason or "Not specified"
                },
                performed_by=deactivated_by
            )
            
            logger.info(f"Deactivated super admin user: {username}")
            
            return {
                "success": True,
                "username": username,
                "message": f"Super admin user '{username}' deactivated successfully"
            }
            
        except Exception as e:
            logger.error(f"Error deactivating super admin {username}: {str(e)}")
            raise
    
    def regenerate_api_key(self, username: str, regenerated_by: str) -> Dict[str, Any]:
        """Regenerate API key for super admin user"""
        try:
            user = db(
                (db.kong_admin_users.username == username) &
                (db.kong_admin_users.is_super_admin == True) &
                (db.kong_admin_users.is_active == True)
            ).select().first()
            
            if not user:
                raise ValueError(f"Active super admin user '{username}' not found")
            
            # Get existing API keys
            existing_keys = self.kong_client.get_consumer_api_keys(username)
            
            # Create new API key
            new_key_data = self.kong_client.create_api_key(
                consumer_username=username,
                tags=["super-admin", "admin-api", "regenerated"]
            )
            
            # Delete old API keys
            for key in existing_keys:
                self.kong_client.delete_api_key(username, key['id'])
            
            # Update database record
            db(db.kong_admin_users.id == user.id).update(
                api_key=new_key_data['key'],
                updated_at=datetime.utcnow()
            )
            
            db.commit()
            
            # Log the action
            self._log_audit_action(
                action="regenerate_api_key",
                resource_type="user",
                resource_id=str(user.id),
                details={
                    "username": username,
                    "old_key_count": len(existing_keys),
                    "new_key_id": new_key_data['id']
                },
                performed_by=regenerated_by
            )
            
            logger.info(f"Regenerated API key for super admin user: {username}")
            
            return {
                "success": True,
                "username": username,
                "new_api_key": new_key_data['key'],
                "message": f"API key regenerated for user '{username}'"
            }
            
        except Exception as e:
            logger.error(f"Error regenerating API key for {username}: {str(e)}")
            raise
    
    def get_audit_log(self, username: Optional[str] = None, action: Optional[str] = None,
                     limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get audit log entries"""
        try:
            query = db.kong_admin_audit_log.id > 0
            
            if username:
                # Get user ID
                user = db(db.kong_admin_users.username == username).select().first()
                if user:
                    query &= db.kong_admin_audit_log.performed_by == user.id
            
            if action:
                query &= db.kong_admin_audit_log.action == action
            
            logs = db(query).select(
                orderby=~db.kong_admin_audit_log.created_at,
                limitby=(offset, offset + limit)
            )
            
            result = []
            for log in logs:
                performer = None
                if log.performed_by:
                    performer_user = db(db.kong_admin_users.id == log.performed_by).select().first()
                    if performer_user:
                        performer = performer_user.username
                
                result.append({
                    "id": log.id,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "performed_by": performer,
                    "ip_address": log.ip_address,
                    "status": log.status,
                    "error_message": log.error_message,
                    "created_at": log.created_at
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting audit log: {str(e)}")
            raise
    
    def _log_audit_action(self, action: str, resource_type: str, resource_id: str,
                         details: Dict[str, Any], performed_by: str,
                         ip_address: Optional[str] = None, user_agent: Optional[str] = None,
                         status: str = "success", error_message: Optional[str] = None):
        """Log audit action"""
        try:
            # Get performer user ID
            performer_user = db(db.kong_admin_users.username == performed_by).select().first()
            performer_id = performer_user.id if performer_user else None
            
            db.kong_admin_audit_log.insert(
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                performed_by=performer_id,
                ip_address=ip_address,
                user_agent=user_agent,
                status=status,
                error_message=error_message
            )
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {str(e)}")
    
    def backup_all_super_admins(self, backup_type: str = "manual",
                               created_by: str = "system") -> Dict[str, Any]:
        """Create backup of all super admin users"""
        try:
            users = db(
                (db.kong_admin_users.is_super_admin == True) &
                (db.kong_admin_users.is_active == True)
            ).select()
            
            backup_results = []
            failed_backups = []
            
            for user in users:
                try:
                    # Create Kong consumer backup
                    kong_backup = self.kong_client.backup_consumer(user.username)
                    
                    # Store backup in database
                    backup_id = db.kong_consumer_backup.insert(
                        kong_consumer_id=user.kong_consumer_id,
                        username=user.username,
                        consumer_data=kong_backup,
                        api_keys=kong_backup.get('api_keys', []),
                        acl_groups=kong_backup.get('acl_groups', []),
                        backup_type=backup_type,
                        created_by=db(db.kong_admin_users.username == created_by).select().first().id if created_by != "system" else None
                    )
                    
                    backup_results.append({
                        "username": user.username,
                        "backup_id": backup_id,
                        "status": "success"
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to backup user {user.username}: {str(e)}")
                    failed_backups.append({
                        "username": user.username,
                        "error": str(e)
                    })
            
            db.commit()
            
            # Log the action
            self._log_audit_action(
                action="backup_all_super_admins",
                resource_type="system",
                resource_id="all_users",
                details={
                    "backup_type": backup_type,
                    "successful_backups": len(backup_results),
                    "failed_backups": len(failed_backups),
                    "backup_results": backup_results,
                    "failed_backups": failed_backups
                },
                performed_by=created_by
            )
            
            return {
                "success": True,
                "total_users": len(users),
                "successful_backups": len(backup_results),
                "failed_backups": len(failed_backups),
                "backup_results": backup_results,
                "failed_backups": failed_backups,
                "message": f"Backup completed. {len(backup_results)} successful, {len(failed_backups)} failed."
            }
            
        except Exception as e:
            logger.error(f"Error backing up super admins: {str(e)}")
            raise