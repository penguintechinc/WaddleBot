"""
Alias Interaction Module for WaddleBot
Handles custom command aliases that execute actions or return text messages
"""

from py4web import action, request, response, DAL, Field, HTTP
from py4web.utils.cors import CORS
import json
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite://storage.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

db = DAL(DATABASE_URL, pool_size=10, migrate=True)

# Define database tables
db.define_table(
    'alias_commands',
    Field('id', 'id'),
    Field('entity_id', 'string', required=True),
    Field('alias', 'string', required=True),
    Field('command_type', 'string', required=True),  # 'text', 'action', 'command'
    Field('response_text', 'text'),
    Field('action_command', 'string'),
    Field('action_parameters', 'json'),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('usage_count', 'integer', default=0),
    Field('last_used', 'datetime'),
    Field('is_active', 'boolean', default=True),
    migrate=True
)

# Create indexes
try:
    db.executesql('CREATE INDEX IF NOT EXISTS idx_alias_commands_entity_alias ON alias_commands(entity_id, alias);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_alias_commands_active ON alias_commands(is_active);')
except Exception as e:
    logger.warning(f"Could not create indexes: {e}")

db.commit()

# CORS setup
CORS(response)

# Module configuration
MODULE_NAME = os.environ.get("MODULE_NAME", "alias_interaction")
MODULE_VERSION = os.environ.get("MODULE_VERSION", "1.0.0")
ROUTER_API_URL = os.environ.get("ROUTER_API_URL", "http://router:8000/router")

@action("health", method=["GET"])
def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "module": MODULE_NAME,
        "version": MODULE_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@action("alias", method=["POST"])
def handle_alias_command():
    """Handle alias command execution (Linux-style aliases)"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        entity_id = data.get("entity_id")
        message_content = data.get("message_content", "")
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        
        if not all([entity_id, message_content, user_id, session_id]):
            raise HTTP(400, "Missing required fields")
        
        # Parse the command
        parts = message_content.strip().split()
        if len(parts) < 2:
            return {
                "success": False,
                "error": "Usage: !alias <subcommand> [args...]"
            }
        
        command_prefix = parts[0]  # Should be !alias
        subcommand = parts[1]
        
        if subcommand == "add":
            # Add a new alias: !alias add !user "!so user"
            return handle_alias_add(entity_id, user_id, parts[2:])
        
        elif subcommand == "remove" or subcommand == "rm":
            # Remove an alias: !alias remove !user
            return handle_alias_remove(entity_id, user_id, parts[2:])
        
        elif subcommand == "list":
            # List all aliases: !alias list
            return handle_alias_list(entity_id)
        
        else:
            return {
                "success": False,
                "error": f"Unknown subcommand: {subcommand}. Use: add, remove, list"
            }
    
    except Exception as e:
        logger.error(f"Error handling alias command: {str(e)}")
        return {
            "success": False,
            "error": f"Error processing alias: {str(e)}"
        }

def handle_alias_add(entity_id, user_id, args):
    """Handle alias add command"""
    try:
        if len(args) < 2:
            return {
                "success": False,
                "error": "Usage: !alias add <alias_name> <command>"
            }
        
        alias_name = args[0]
        # Join the rest as the command, handling quoted strings
        command_text = " ".join(args[1:])
        
        # Remove quotes if present
        if command_text.startswith('"') and command_text.endswith('"'):
            command_text = command_text[1:-1]
        elif command_text.startswith("'") and command_text.endswith("'"):
            command_text = command_text[1:-1]
        
        # Check if alias already exists
        existing = db(
            (db.alias_commands.entity_id == entity_id) &
            (db.alias_commands.alias == alias_name) &
            (db.alias_commands.is_active == True)
        ).select().first()
        
        if existing:
            return {
                "success": False,
                "error": f"Alias '{alias_name}' already exists. Use '!alias remove {alias_name}' first."
            }
        
        # Create the alias
        alias_id = db.alias_commands.insert(
            entity_id=entity_id,
            alias=alias_name,
            command_type="command",
            response_text=command_text,
            action_command=command_text,
            created_by=user_id
        )
        
        db.commit()
        
        return {
            "success": True,
            "response_action": "chat",
            "response_data": {
                "message": f"Alias '{alias_name}' created for command: {command_text}"
            }
        }
    
    except Exception as e:
        logger.error(f"Error adding alias: {str(e)}")
        return {
            "success": False,
            "error": f"Error adding alias: {str(e)}"
        }

def handle_alias_remove(entity_id, user_id, args):
    """Handle alias remove command"""
    try:
        if len(args) < 1:
            return {
                "success": False,
                "error": "Usage: !alias remove <alias_name>"
            }
        
        alias_name = args[0]
        
        # Find the alias
        alias = db(
            (db.alias_commands.entity_id == entity_id) &
            (db.alias_commands.alias == alias_name) &
            (db.alias_commands.is_active == True)
        ).select().first()
        
        if not alias:
            return {
                "success": False,
                "error": f"Alias '{alias_name}' not found"
            }
        
        # Soft delete the alias
        db.alias_commands[alias.id] = dict(is_active=False)
        db.commit()
        
        return {
            "success": True,
            "response_action": "chat",
            "response_data": {
                "message": f"Alias '{alias_name}' removed"
            }
        }
    
    except Exception as e:
        logger.error(f"Error removing alias: {str(e)}")
        return {
            "success": False,
            "error": f"Error removing alias: {str(e)}"
        }

def handle_alias_list(entity_id):
    """Handle alias list command"""
    try:
        aliases = db(
            (db.alias_commands.entity_id == entity_id) &
            (db.alias_commands.is_active == True)
        ).select(
            orderby=db.alias_commands.alias
        )
        
        if not aliases:
            return {
                "success": True,
                "response_action": "chat",
                "response_data": {
                    "message": "No aliases configured"
                }
            }
        
        alias_list = []
        for alias in aliases:
            alias_list.append(f"{alias.alias} -> {alias.action_command}")
        
        message = "Configured aliases:\n" + "\n".join(alias_list)
        
        return {
            "success": True,
            "response_action": "chat",
            "response_data": {
                "message": message
            }
        }
    
    except Exception as e:
        logger.error(f"Error listing aliases: {str(e)}")
        return {
            "success": False,
            "error": f"Error listing aliases: {str(e)}"
        }

@action("execute_alias", method=["POST"])
def execute_alias():
    """Execute a defined alias"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        entity_id = data.get("entity_id")
        message_content = data.get("message_content", "")
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        
        if not all([entity_id, message_content, user_id, session_id]):
            raise HTTP(400, "Missing required fields")
        
        # Parse the command to get alias name
        parts = message_content.strip().split()
        if not parts:
            return {
                "success": False,
                "error": "Empty command"
            }
        
        alias_name = parts[0]  # This should be the alias like !user
        alias_args = parts[1:] if len(parts) > 1 else []
        
        # Look up the alias
        alias_command = db(
            (db.alias_commands.entity_id == entity_id) &
            (db.alias_commands.alias == alias_name) &
            (db.alias_commands.is_active == True)
        ).select().first()
        
        if not alias_command:
            return {
                "success": False,
                "error": f"Alias '{alias_name}' not found"
            }
        
        # Update usage statistics
        db.alias_commands[alias_command.id] = dict(
            usage_count=alias_command.usage_count + 1,
            last_used=datetime.utcnow()
        )
        db.commit()
        
        # Execute the aliased command
        aliased_command = alias_command.action_command
        
        # Replace placeholders in the command
        aliased_command = replace_alias_variables(aliased_command, {
            "user": user_id,
            "args": alias_args,
            "all_args": " ".join(alias_args)
        })
        
        # Execute the command through the router
        return execute_command_through_router(
            aliased_command,
            entity_id,
            user_id,
            session_id
        )
    
    except Exception as e:
        logger.error(f"Error executing alias: {str(e)}")
        return {
            "success": False,
            "error": f"Error executing alias: {str(e)}"
        }

@action("alias/create", method=["POST"])
def create_alias():
    """Create a new alias command"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        entity_id = data.get("entity_id")
        alias = data.get("alias")
        command_type = data.get("command_type")
        created_by = data.get("created_by")
        
        if not all([entity_id, alias, command_type, created_by]):
            raise HTTP(400, "Missing required fields")
        
        # Validate command type
        if command_type not in ["text", "action", "command"]:
            raise HTTP(400, "Invalid command type")
        
        # Check if alias already exists
        existing = db(
            (db.alias_commands.entity_id == entity_id) &
            (db.alias_commands.alias == alias) &
            (db.alias_commands.is_active == True)
        ).select().first()
        
        if existing:
            raise HTTP(409, f"Alias '{alias}' already exists")
        
        # Create the alias
        alias_id = db.alias_commands.insert(
            entity_id=entity_id,
            alias=alias,
            command_type=command_type,
            response_text=data.get("response_text"),
            action_command=data.get("action_command"),
            action_parameters=data.get("action_parameters"),
            created_by=created_by
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Alias '{alias}' created successfully",
            "alias_id": alias_id
        }
    
    except Exception as e:
        logger.error(f"Error creating alias: {str(e)}")
        raise HTTP(500, f"Error creating alias: {str(e)}")

@action("alias/list", method=["GET"])
def list_aliases():
    """List all aliases for an entity"""
    try:
        entity_id = request.query.get("entity_id")
        if not entity_id:
            raise HTTP(400, "Missing entity_id parameter")
        
        aliases = db(
            (db.alias_commands.entity_id == entity_id) &
            (db.alias_commands.is_active == True)
        ).select(
            orderby=db.alias_commands.alias
        )
        
        alias_list = []
        for alias in aliases:
            alias_data = dict(alias)
            alias_data["created_at"] = alias.created_at.isoformat() if alias.created_at else None
            alias_data["updated_at"] = alias.updated_at.isoformat() if alias.updated_at else None
            alias_data["last_used"] = alias.last_used.isoformat() if alias.last_used else None
            alias_list.append(alias_data)
        
        return {
            "success": True,
            "aliases": alias_list,
            "total": len(alias_list)
        }
    
    except Exception as e:
        logger.error(f"Error listing aliases: {str(e)}")
        raise HTTP(500, f"Error listing aliases: {str(e)}")

@action("alias/update", method=["PUT"])
def update_alias():
    """Update an existing alias"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        alias_id = data.get("alias_id")
        entity_id = data.get("entity_id")
        
        if not all([alias_id, entity_id]):
            raise HTTP(400, "Missing required fields")
        
        # Get the existing alias
        alias = db(
            (db.alias_commands.id == alias_id) &
            (db.alias_commands.entity_id == entity_id)
        ).select().first()
        
        if not alias:
            raise HTTP(404, "Alias not found")
        
        # Update fields
        update_data = {}
        if "response_text" in data:
            update_data["response_text"] = data["response_text"]
        if "action_command" in data:
            update_data["action_command"] = data["action_command"]
        if "action_parameters" in data:
            update_data["action_parameters"] = data["action_parameters"]
        if "is_active" in data:
            update_data["is_active"] = data["is_active"]
        
        if update_data:
            db.alias_commands[alias_id] = update_data
            db.commit()
        
        return {
            "success": True,
            "message": f"Alias '{alias.alias}' updated successfully"
        }
    
    except Exception as e:
        logger.error(f"Error updating alias: {str(e)}")
        raise HTTP(500, f"Error updating alias: {str(e)}")

@action("alias/delete", method=["DELETE"])
def delete_alias():
    """Delete an alias (soft delete)"""
    try:
        data = request.json
        if not data:
            raise HTTP(400, "No data provided")
        
        alias_id = data.get("alias_id")
        entity_id = data.get("entity_id")
        
        if not all([alias_id, entity_id]):
            raise HTTP(400, "Missing required fields")
        
        # Get the existing alias
        alias = db(
            (db.alias_commands.id == alias_id) &
            (db.alias_commands.entity_id == entity_id)
        ).select().first()
        
        if not alias:
            raise HTTP(404, "Alias not found")
        
        # Soft delete
        db.alias_commands[alias_id] = dict(is_active=False)
        db.commit()
        
        return {
            "success": True,
            "message": f"Alias '{alias.alias}' deleted successfully"
        }
    
    except Exception as e:
        logger.error(f"Error deleting alias: {str(e)}")
        raise HTTP(500, f"Error deleting alias: {str(e)}")

def replace_variables(text, variables):
    """Replace variables in text with actual values"""
    for key, value in variables.items():
        text = text.replace(f"{{{key}}}", str(value))
    return text

def replace_alias_variables(command, variables):
    """Replace variables in aliased commands"""
    # Replace {user} with the user who triggered the alias
    if "{user}" in command:
        command = command.replace("{user}", str(variables.get("user", "")))
    
    # Replace {args} with individual arguments
    args = variables.get("args", [])
    for i, arg in enumerate(args):
        command = command.replace(f"{{arg{i+1}}}", str(arg))
    
    # Replace {all_args} with all arguments as a single string
    if "{all_args}" in command:
        command = command.replace("{all_args}", variables.get("all_args", ""))
    
    # Replace user keyword with first argument (common pattern)
    if "user" in command and args:
        command = command.replace("user", args[0])
    
    return command

def execute_command_through_router(command, entity_id, user_id, session_id):
    """Execute a command through the router"""
    try:
        import requests
        
        # Send to router
        payload = {
            "entity_id": entity_id,
            "user_id": user_id,
            "session_id": session_id,
            "message_content": command,
            "message_type": "chatMessage"
        }
        
        response = requests.post(f"{ROUTER_API_URL}/events", json=payload, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "response_action": "chat",
                "response_data": {
                    "message": f"Executed: {command}"
                }
            }
        else:
            return {
                "success": False,
                "error": f"Failed to execute command: {response.text}"
            }
    
    except Exception as e:
        logger.error(f"Error executing command through router: {str(e)}")
        return {
            "success": False,
            "error": f"Error executing command: {str(e)}"
        }

def execute_action(action_command, parameters, context):
    """Execute an action with parameters"""
    try:
        # Handle different action types
        if action_command == "random_response":
            # Random response from a list
            responses = parameters.get("responses", [])
            if responses:
                import random
                response = random.choice(responses)
                return {
                    "success": True,
                    "response_action": "chat",
                    "response_data": {
                        "message": replace_variables(response, {
                            "user": context["user_id"],
                            "args": " ".join(context["args"])
                        })
                    }
                }
        
        elif action_command == "counter":
            # Increment/decrement a counter
            counter_name = parameters.get("counter_name", "default")
            increment = parameters.get("increment", 1)
            
            # Get or create counter
            counter = db(
                (db.alias_commands.entity_id == context["entity_id"]) &
                (db.alias_commands.alias == f"__counter_{counter_name}") &
                (db.alias_commands.command_type == "counter")
            ).select().first()
            
            if not counter:
                # Create counter
                counter_id = db.alias_commands.insert(
                    entity_id=context["entity_id"],
                    alias=f"__counter_{counter_name}",
                    command_type="counter",
                    response_text="0",
                    created_by="system"
                )
                counter_value = 0
            else:
                counter_value = int(counter.response_text or 0)
            
            # Update counter
            new_value = counter_value + increment
            if counter:
                db.alias_commands[counter.id] = dict(response_text=str(new_value))
            else:
                db.alias_commands[counter_id] = dict(response_text=str(new_value))
            
            db.commit()
            
            return {
                "success": True,
                "response_action": "chat",
                "response_data": {
                    "message": f"{counter_name}: {new_value}"
                }
            }
        
        elif action_command == "time":
            # Display current time
            from datetime import datetime
            now = datetime.utcnow()
            format_str = parameters.get("format", "%Y-%m-%d %H:%M:%S UTC")
            time_str = now.strftime(format_str)
            
            return {
                "success": True,
                "response_action": "chat",
                "response_data": {
                    "message": f"Current time: {time_str}"
                }
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown action: {action_command}"
            }
    
    except Exception as e:
        logger.error(f"Error executing action {action_command}: {str(e)}")
        return {
            "success": False,
            "error": f"Error executing action: {str(e)}"
        }

def execute_command(command, entity_id, user_id, session_id, args):
    """Execute another WaddleBot command"""
    try:
        import requests
        
        # Construct the command message
        command_message = f"{command} {' '.join(args)}"
        
        # Send to router
        payload = {
            "entity_id": entity_id,
            "user_id": user_id,
            "session_id": session_id,
            "message_content": command_message,
            "message_type": "chatMessage"
        }
        
        response = requests.post(f"{ROUTER_API_URL}/events", json=payload, timeout=30)
        
        if response.status_code == 200:
            return {
                "success": True,
                "response_action": "chat",
                "response_data": {
                    "message": f"Executed command: {command_message}"
                }
            }
        else:
            return {
                "success": False,
                "error": f"Failed to execute command: {response.text}"
            }
    
    except Exception as e:
        logger.error(f"Error executing command {command}: {str(e)}")
        return {
            "success": False,
            "error": f"Error executing command: {str(e)}"
        }

if __name__ == "__main__":
    from py4web import start
    start(port=8010, host="0.0.0.0")