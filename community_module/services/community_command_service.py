"""
Community command service for handling community management commands
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ..models import db, GLOBAL_COMMUNITY_ID
from ...reputation_module.services.community_service import CommunityService
from ...reputation_module.services.entity_group_service import EntityGroupService
from ...router_module.services.rbac_service import rbac_service

logger = logging.getLogger(__name__)

class CommunityCommandService:
    """Service for processing community management commands"""
    
    def __init__(self):
        self.community_service = CommunityService()
        self.entity_group_service = EntityGroupService()
        
        # Command patterns
        self.command_patterns = {
            'create': r'^!community\s+create\s+(.+)$',
            'context': r'^!community\s+context\s+(.+)$',
            'add_entity': r'^!community\s+add\s+entity\s+(.+)$',
            'add_user': r'^!community\s+add\s+user\s+(.+)$',
            'install': r'^!community\s+install\s+(.+)$',
            'list': r'^!community\s+list$',
            'info': r'^!community\s+info(?:\s+(.+))?$',
            'leave': r'^!community\s+leave$',
            'members': r'^!community\s+members$',
            'portal_login': r'^!community\s+portal\s+login\s+add\s+(.+)$',
            'help': r'^!community\s+help$'
        }
    
    def check_command_permission(self, user_id: str, entity_id: str, command_type: str, 
                                current_context: Dict[str, Any]) -> bool:
        """Check if user has permission to execute a command"""
        try:
            # Define command permission requirements
            command_permissions = {
                'create': 'community.add_entity',  # Can create communities
                'context': 'commands.basic',       # Basic command access
                'add_entity': 'community.add_entity',  # Can add entities to communities
                'add_user': 'community.add_user',  # Can add users to communities
                'install': 'community.install_modules',  # Can install modules
                'list': 'commands.basic',          # Basic command access
                'info': 'commands.basic',          # Basic command access
                'leave': 'commands.basic',         # Basic command access
                'members': 'commands.basic',       # Basic command access
                'portal_login': 'community.manage_settings',  # Can manage community settings
                'help': 'commands.basic'           # Basic command access
            }
            
            required_permission = command_permissions.get(command_type, 'commands.basic')
            
            # Check permission based on current context
            if current_context and current_context.get('community_id'):
                # Check community-specific permission
                return rbac_service.has_permission(
                    user_id, required_permission, 
                    entity_id=entity_id, 
                    community_id=current_context['community_id']
                )
            else:
                # Check global permission
                return rbac_service.has_permission(
                    user_id, required_permission, 
                    entity_id=entity_id
                )
                
        except Exception as e:
            logger.error(f"Error checking command permission: {str(e)}")
            return False
    
    def process_command(self, user_id: str, entity_id: str, message_content: str,
                       session_id: str, execution_id: str) -> Dict[str, Any]:
        """Process a community command"""
        try:
            # Ensure user has access to global community with default role
            rbac_service.ensure_user_in_global_community(user_id)
            
            # Get current user context
            current_context = self.get_user_context(user_id, entity_id)
            
            # Parse command
            command_type, args = self.parse_command(message_content)
            
            if not command_type:
                return {
                    "success": False,
                    "message": "Invalid community command. Use `!community help` for available commands."
                }
            
            # Check permissions for the command
            if not self.check_command_permission(user_id, entity_id, command_type, current_context):
                return {
                    "success": False,
                    "message": "You don't have permission to execute this command."
                }
            
            # Route to appropriate handler
            if command_type == 'create':
                return self.handle_create_command(user_id, entity_id, args, session_id)
            elif command_type == 'context':
                return self.handle_context_command(user_id, entity_id, args)
            elif command_type == 'add_entity':
                return self.handle_add_entity_command(user_id, entity_id, args, current_context)
            elif command_type == 'add_user':
                return self.handle_add_user_command(user_id, entity_id, args, current_context)
            elif command_type == 'install':
                return self.handle_install_command(user_id, entity_id, args, current_context)
            elif command_type == 'list':
                return self.handle_list_command(user_id)
            elif command_type == 'info':
                return self.handle_info_command(user_id, args, current_context)
            elif command_type == 'leave':
                return self.handle_leave_command(user_id, entity_id, current_context)
            elif command_type == 'members':
                return self.handle_members_command(user_id, current_context)
            elif command_type == 'portal_login':
                return self.handle_portal_login_command(user_id, entity_id, args, current_context)
            elif command_type == 'help':
                return self.handle_help_command()
            else:
                return {
                    "success": False,
                    "message": "Unknown community command. Use `!community help` for available commands."
                }
                
        except Exception as e:
            logger.error(f"Error processing community command: {str(e)}")
            return {
                "success": False,
                "message": "An error occurred while processing your command.",
                "error": str(e)
            }
    
    def parse_command(self, message_content: str) -> tuple[Optional[str], Optional[str]]:
        """Parse community command and extract type and arguments"""
        message_content = message_content.strip()
        
        for command_type, pattern in self.command_patterns.items():
            match = re.match(pattern, message_content, re.IGNORECASE)
            if match:
                args = match.group(1) if match.groups() else None
                return command_type, args
        
        return None, None
    
    def get_user_context(self, user_id: str, entity_id: str) -> Optional[int]:
        """Get user's current community context"""
        try:
            context = db(
                (db.user_context.user_id == user_id) &
                (db.user_context.entity_id == entity_id)
            ).select(orderby=~db.user_context.set_at).first()
            
            if context:
                # Check if context is expired
                if context.expires_at and context.expires_at < datetime.utcnow():
                    return None
                return context.current_community_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user context: {str(e)}")
            return None
    
    def set_user_context(self, user_id: str, entity_id: str, community_id: int) -> None:
        """Set user's current community context"""
        try:
            # Remove existing context
            db(
                (db.user_context.user_id == user_id) &
                (db.user_context.entity_id == entity_id)
            ).delete()
            
            # Set new context (expires in 1 hour)
            db.user_context.insert(
                user_id=user_id,
                entity_id=entity_id,
                current_community_id=community_id,
                set_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error setting user context: {str(e)}")
    
    def handle_create_command(self, user_id: str, entity_id: str, community_name: str,
                             session_id: str) -> Dict[str, Any]:
        """Handle community create command"""
        try:
            # Return form for creating community
            return {
                "success": True,
                "response_type": "form",
                "form_title": f"Create Community: {community_name}",
                "form_description": f"Create a new community called '{community_name}'. You will be the owner.",
                "form_fields": [
                    {
                        "name": "community_name",
                        "type": "text",
                        "label": "Community Name",
                        "value": community_name,
                        "required": True
                    },
                    {
                        "name": "description",
                        "type": "textarea",
                        "label": "Description",
                        "placeholder": "Describe your community...",
                        "required": False
                    },
                    {
                        "name": "user_id",
                        "type": "hidden",
                        "value": user_id
                    },
                    {
                        "name": "entity_id",
                        "type": "hidden",
                        "value": entity_id
                    },
                    {
                        "name": "session_id",
                        "type": "hidden",
                        "value": session_id
                    },
                    {
                        "name": "action",
                        "type": "hidden",
                        "value": "create_community"
                    }
                ],
                "form_submit_url": "/community/form",
                "form_submit_method": "POST"
            }
            
        except Exception as e:
            logger.error(f"Error handling create command: {str(e)}")
            return {
                "success": False,
                "message": f"Error creating community form: {str(e)}"
            }
    
    def handle_context_command(self, user_id: str, entity_id: str, 
                              community_name: str) -> Dict[str, Any]:
        """Handle community context command"""
        try:
            # Get community by name
            result = self.community_service.get_community_by_name(community_name)
            
            if not result["success"]:
                return {
                    "success": False,
                    "message": f"Community '{community_name}' not found."
                }
            
            community = result["community"]
            
            # Check if user has permission to access this community
            if not self.community_service.check_user_permission(community["id"], user_id):
                return {
                    "success": False,
                    "message": f"You don't have permission to access community '{community_name}'."
                }
            
            # Set user context
            self.set_user_context(user_id, entity_id, community["id"])
            
            return {
                "success": True,
                "message": f"✅ Switched to community context: **{community_name}**\\n"
                          f"You can now use community-specific commands like:\\n"
                          f"• `!community add entity <entity_id>`\\n"
                          f"• `!community add user <user_id>`\\n"
                          f"• `!community install <module_id>`\\n"
                          f"• `!community info` - View community details\\n"
                          f"• `!community members` - List community members"
            }
            
        except Exception as e:
            logger.error(f"Error handling context command: {str(e)}")
            return {
                "success": False,
                "message": f"Error switching community context: {str(e)}"
            }
    
    def handle_add_entity_command(self, user_id: str, entity_id: str, 
                                 target_entity_id: str, current_context: Optional[int]) -> Dict[str, Any]:
        """Handle add entity command"""
        try:
            if not current_context:
                return {
                    "success": False,
                    "message": "No community context set. Use `!community context <name>` first."
                }
            
            # Check if user has permission to manage this community
            if not self.community_service.check_user_permission(current_context, user_id, "moderator"):
                return {
                    "success": False,
                    "message": "You don't have permission to add entities to this community."
                }
            
            # Add entity to community
            result = self.community_service.add_entity_to_community(
                current_context, target_entity_id, user_id
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"✅ Entity `{target_entity_id}` added to community."
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Failed to add entity: {result['error']}"
                }
            
        except Exception as e:
            logger.error(f"Error handling add entity command: {str(e)}")
            return {
                "success": False,
                "message": f"Error adding entity: {str(e)}"
            }
    
    def handle_add_user_command(self, user_id: str, entity_id: str, 
                               target_user_id: str, current_context: Optional[int]) -> Dict[str, Any]:
        """Handle add user command"""
        try:
            if not current_context:
                return {
                    "success": False,
                    "message": "No community context set. Use `!community context <name>` first."
                }
            
            # Check if user has permission to manage this community
            if not self.community_service.check_user_permission(current_context, user_id, "moderator"):
                return {
                    "success": False,
                    "message": "You don't have permission to add users to this community."
                }
            
            # Add user to community
            result = self.community_service.add_user_to_community(
                current_context, target_user_id, user_id
            )
            
            if result["success"]:
                return {
                    "success": True,
                    "message": f"✅ User `{target_user_id}` added to community."
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Failed to add user: {result['error']}"
                }
            
        except Exception as e:
            logger.error(f"Error handling add user command: {str(e)}")
            return {
                "success": False,
                "message": f"Error adding user: {str(e)}"
            }
    
    def handle_install_command(self, user_id: str, entity_id: str, 
                              module_id: str, current_context: Optional[int]) -> Dict[str, Any]:
        """Handle install module command"""
        try:
            if not current_context:
                return {
                    "success": False,
                    "message": "No community context set. Use `!community context <name>` first."
                }
            
            # Check if user has permission to install modules
            if not self.community_service.check_user_permission(current_context, user_id, "admin"):
                return {
                    "success": False,
                    "message": "You don't have permission to install modules in this community."
                }
            
            # TODO: Implement module installation
            # This would integrate with the marketplace module
            return {
                "success": True,
                "message": f"🔧 Module installation for `{module_id}` is not yet implemented. "
                          f"This will integrate with the marketplace module."
            }
            
        except Exception as e:
            logger.error(f"Error handling install command: {str(e)}")
            return {
                "success": False,
                "message": f"Error installing module: {str(e)}"
            }
    
    def handle_list_command(self, user_id: str) -> Dict[str, Any]:
        """Handle list communities command"""
        try:
            communities = self.community_service.get_user_communities(user_id)
            
            if not communities:
                return {
                    "success": True,
                    "message": "You are not a member of any communities."
                }
            
            message = "**Your Communities:**\\n"
            for community in communities:
                role_icon = "👑" if community["is_owner"] else "🔹"
                message += f"{role_icon} **{community['name']}** ({community['role']})\\n"
                if community.get('description'):
                    message += f"   _{community['description']}_\\n"
                message += f"   Members: {community['member_count']} | Entity Groups: {community['entity_group_count']}\\n\\n"
            
            return {
                "success": True,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error handling list command: {str(e)}")
            return {
                "success": False,
                "message": f"Error listing communities: {str(e)}"
            }
    
    def handle_info_command(self, user_id: str, community_name: Optional[str], 
                           current_context: Optional[int]) -> Dict[str, Any]:
        """Handle community info command"""
        try:
            if community_name:
                # Get specific community info
                result = self.community_service.get_community_by_name(community_name)
                if not result["success"]:
                    return {
                        "success": False,
                        "message": f"Community '{community_name}' not found."
                    }
                community = result["community"]
            elif current_context:
                # Get current context community info
                result = self.community_service.get_community(current_context)
                if not result["success"]:
                    return {
                        "success": False,
                        "message": "Current community context not found."
                    }
                community = result["community"]
            else:
                return {
                    "success": False,
                    "message": "No community specified and no context set. Use `!community info <name>` or set context first."
                }
            
            # Check permission
            if not self.community_service.check_user_permission(community["id"], user_id):
                return {
                    "success": False,
                    "message": "You don't have permission to view this community's information."
                }
            
            # Get members
            members = self.community_service.get_community_members(community["id"])
            
            message = f"**Community: {community['name']}**\\n"
            if community.get('description'):
                message += f"_{community['description']}_\\n\\n"
            
            message += f"**Details:**\\n"
            message += f"• Created: {community['created_at'][:10]}\\n"
            message += f"• Members: {len(members)}\\n"
            message += f"• Entity Groups: {len(community['entity_groups'])}\\n"
            message += f"• Owners: {', '.join(community['owners'])}\\n"
            
            return {
                "success": True,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error handling info command: {str(e)}")
            return {
                "success": False,
                "message": f"Error getting community info: {str(e)}"
            }
    
    def handle_leave_command(self, user_id: str, entity_id: str, 
                            current_context: Optional[int]) -> Dict[str, Any]:
        """Handle leave community command"""
        try:
            if not current_context:
                return {
                    "success": False,
                    "message": "No community context set. Use `!community context <name>` first."
                }
            
            # Can't leave global community
            if current_context == GLOBAL_COMMUNITY_ID:
                return {
                    "success": False,
                    "message": "Cannot leave the global community."
                }
            
            # Remove user from community
            result = self.community_service.remove_user_from_community(current_context, user_id)
            
            if result["success"]:
                # Clear context
                db(
                    (db.user_context.user_id == user_id) &
                    (db.user_context.entity_id == entity_id)
                ).delete()
                db.commit()
                
                return {
                    "success": True,
                    "message": "✅ You have left the community."
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Failed to leave community: {result['error']}"
                }
            
        except Exception as e:
            logger.error(f"Error handling leave command: {str(e)}")
            return {
                "success": False,
                "message": f"Error leaving community: {str(e)}"
            }
    
    def handle_members_command(self, user_id: str, current_context: Optional[int]) -> Dict[str, Any]:
        """Handle list members command"""
        try:
            if not current_context:
                return {
                    "success": False,
                    "message": "No community context set. Use `!community context <name>` first."
                }
            
            # Check permission
            if not self.community_service.check_user_permission(current_context, user_id):
                return {
                    "success": False,
                    "message": "You don't have permission to view community members."
                }
            
            # Get members
            members = self.community_service.get_community_members(current_context)
            
            if not members:
                return {
                    "success": True,
                    "message": "This community has no members."
                }
            
            message = "**Community Members:**\\n"
            for member in members:
                role_icon = {"owner": "👑", "admin": "⚡", "moderator": "🛡️", "member": "👤"}.get(member["role"], "👤")
                message += f"{role_icon} **{member['user_id']}** ({member['role']})\\n"
                message += f"   Joined: {member['joined_at'][:10]}\\n"
                if member.get('invited_by'):
                    message += f"   Invited by: {member['invited_by']}\\n"
                message += "\\n"
            
            return {
                "success": True,
                "message": message
            }
            
        except Exception as e:
            logger.error(f"Error handling members command: {str(e)}")
            return {
                "success": False,
                "message": f"Error listing members: {str(e)}"
            }
    
    def handle_help_command(self) -> Dict[str, Any]:
        """Handle help command"""
        message = """**Community Commands:**

**Basic Commands:**
• `!community help` - Show this help message
• `!community list` - List your communities
• `!community create <name>` - Create a new community
• `!community context <name>` - Switch to community context

**Context Commands (require community context):**
• `!community info` - Show current community info
• `!community members` - List community members
• `!community add entity <entity_id>` - Add entity to community
• `!community add user <user_id>` - Add user to community
• `!community install <module_id>` - Install module (admin only)
• `!community leave` - Leave current community

**Notes:**
• Use `!community context <name>` to switch to a community before using context commands
• Only community moderators+ can add entities/users
• Only community admins+ can install modules
• Community owners have full control"""
        
        return {
            "success": True,
            "message": message
        }
    
    def handle_portal_login_command(self, user_id: str, entity_id: str, args: str, 
                                   current_context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle portal login creation command"""
        try:
            import requests
            import os
            
            # Check if user is community owner
            if not current_context or not current_context.get('community_id'):
                return {
                    "success": False,
                    "message": "You must be in a community context to use portal login. Use `!community context <name>` first."
                }
            
            community_id = current_context['community_id']
            
            # Verify user is owner of the community
            user_role = rbac_service.get_user_role_in_community(user_id, community_id)
            if user_role != 'owner':
                return {
                    "success": False,
                    "message": "Only community owners can create portal login access."
                }
            
            # Parse email from args
            email = args.strip()
            if not email or '@' not in email:
                return {
                    "success": False,
                    "message": "Please provide a valid email address. Usage: `!community portal login add your@email.com`"
                }
            
            # Get community info
            community = db(
                (db.communities.id == community_id) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not community:
                return {
                    "success": False,
                    "message": "Community not found."
                }
            
            # Create portal user
            auth_service = PortalAuthService(portal_db)
            result = auth_service.create_portal_user(
                user_id=user_id,
                email=email,
                display_name=args.split('@')[0]  # Use part before @ as display name
            )
            
            if not result['success']:
                if 'already exists' in result['error']:
                    return {
                        "success": False,
                        "message": "Portal access already exists for this user ID. Check your email for the previous temporary password."
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to create portal access: {result['error']}"
                    }
            
            # Send email with temporary password
            email_service = EmailService()
            email_result = email_service.send_temp_password(
                email=email,
                user_id=user_id,
                display_name=result.get('display_name', user_id),
                temp_password=result['temp_password'],
                expires_at=result['expires_at'].isoformat()
            )
            
            if email_result['success']:
                portal_url = os.environ.get('PORTAL_URL', 'http://localhost:8000')
                return {
                    "success": True,
                    "message": f"Portal access created! Check your email at {email} for login credentials. Portal URL: {portal_url}",
                    "response_action": "chat"
                }
            else:
                return {
                    "success": True,
                    "message": f"Portal access created, but email failed to send. Your temporary password: {result['temp_password']} (expires in 24 hours)",
                    "response_action": "chat"
                }
                
        except Exception as e:
            logger.error(f"Error handling portal login command: {str(e)}")
            return {
                "success": False,
                "message": "Error creating portal access. Please try again."
            }
    
    def process_form_submission(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process form submission from community commands"""
        try:
            action = form_data.get("action")
            
            if action == "create_community":
                return self.process_create_community_form(form_data)
            else:
                return {
                    "success": False,
                    "message": "Unknown form action."
                }
                
        except Exception as e:
            logger.error(f"Error processing form submission: {str(e)}")
            return {
                "success": False,
                "message": "Error processing form submission.",
                "error": str(e)
            }
    
    def process_create_community_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process create community form submission"""
        try:
            community_name = form_data.get("community_name", "").strip()
            description = form_data.get("description", "").strip()
            user_id = form_data.get("user_id")
            entity_id = form_data.get("entity_id")
            
            if not community_name:
                return {
                    "success": False,
                    "message": "Community name is required."
                }
            
            # Create community
            result = self.community_service.create_community(
                name=community_name,
                created_by=user_id,
                description=description
            )
            
            if result["success"]:
                community = result["community"]
                
                # Set user context to the new community
                self.set_user_context(user_id, entity_id, community["id"])
                
                return {
                    "success": True,
                    "message": f"✅ Community **{community_name}** created successfully!\\n"
                              f"You are now in the community context and can use community-specific commands."
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ Failed to create community: {result['error']}"
                }
                
        except Exception as e:
            logger.error(f"Error processing create community form: {str(e)}")
            return {
                "success": False,
                "message": f"Error creating community: {str(e)}"
            }