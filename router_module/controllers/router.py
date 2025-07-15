"""
Main router controller for handling incoming events from collectors
"""

import json
import logging
import asyncio
import time
import os
from datetime import datetime, timedelta
from py4web import action, request, response, HTTP
from typing import List, Dict, Any

from ..models import db
from ..services.command_processor import command_processor, CommandRequest
from ..services.auth_service import require_api_key
from ..services.session_manager import session_manager
from ..services.rbac_service import rbac_service
from ..middleware.rbac_middleware import rbac_middleware, require_permission, require_role
from ..config import load_config
import requests

logger = logging.getLogger(__name__)

# Load configuration
router_config, lambda_config, openwhisk_config, waddlebot_config = load_config()

# Initialize RBAC system on startup
try:
    rbac_service.initialize_rbac_system()
    logger.info("RBAC system initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize RBAC system: {str(e)}")
    # Continue startup even if RBAC initialization fails

def ensure_user_global_community_access(user_id: str) -> None:
    """Ensure user has access to global community with default role"""
    try:
        rbac_service.ensure_user_in_global_community(user_id)
        logger.debug(f"Ensured user {user_id} has access to global community")
    except Exception as e:
        logger.error(f"Error ensuring user {user_id} global community access: {str(e)}")

def await_process_reputation_event(user_id: str, entity_id: str, message_type: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process reputation event asynchronously"""
    try:
        # Map message types to reputation events
        event_name_mapping = {
            "chatMessage": "message",
            "subscription": "sub",
            "follow": "follow",
            "donation": "donation",
            "cheer": "cheer",
            "raid": "raid",
            "host": "host",
            "subgift": "subgift",
            "resub": "resub",
            "reaction": "reaction",
            "member_join": "member_join",
            "member_leave": "member_leave",
            "voice_join": "voice_join",
            "voice_leave": "voice_leave",
            "voice_time": "voice_time",
            "boost": "boost",
            "ban": "ban",
            "kick": "kick",
            "timeout": "timeout",
            "warn": "warn",
            "file_share": "file_share",
            "app_mention": "app_mention",
            "channel_join": "channel_join"
        }
        
        event_name = event_name_mapping.get(message_type, message_type)
        
        # Prepare reputation event data
        reputation_payload = {
            "user_id": user_id,
            "entity_id": entity_id,
            "event_name": event_name,
            "event_data": {
                "platform": event_data.get("platform"),
                "server_id": event_data.get("server_id"),
                "channel_id": event_data.get("channel_id"),
                "message_content": event_data.get("message_content"),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        # Add message-type specific data
        if message_type == "cheer" and "bits" in event_data:
            reputation_payload["event_data"]["bits"] = event_data["bits"]
        elif message_type == "voice_time" and "minutes" in event_data:
            reputation_payload["event_data"]["minutes"] = event_data["minutes"]
        elif message_type == "donation" and "amount" in event_data:
            reputation_payload["event_data"]["amount"] = event_data["amount"]
        
        # Send to reputation module
        reputation_url = os.environ.get("REPUTATION_MODULE_URL", "http://reputation-module:8000")
        
        response = requests.post(
            f"{reputation_url}/reputation/process",
            json=reputation_payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            return {"success": True, "data": response.json()}
        else:
            logger.warning(f"Reputation processing failed: {response.status_code} - {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except requests.RequestException as e:
        logger.error(f"Error sending reputation event: {str(e)}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.error(f"Error processing reputation event: {str(e)}")
        return {"success": False, "error": str(e)}

def get_event_triggered_modules(message_type: str, entity_id: str) -> List[Dict[str, Any]]:
    """Get modules that should be triggered by this event type"""
    try:
        # Get modules that are triggered by this event type or both commands and events
        modules = db(
            (db.commands.is_active == True) &
            (db.commands.trigger_type.belongs(['event', 'both'])) &
            (db.commands.event_types.contains(message_type))
        ).select(orderby=db.commands.priority)
        
        # Check permissions for entity
        authorized_modules = []
        for module in modules:
            # Check if entity has permission to use this module
            permission = db(
                (db.command_permissions.command_id == module.id) &
                (db.command_permissions.entity_id == entity_id) &
                (db.command_permissions.is_enabled == True)
            ).select().first()
            
            if permission:
                authorized_modules.append({
                    "id": module.id,
                    "command": module.command,
                    "location_url": module.location_url,
                    "method": module.method,
                    "headers": module.headers,
                    "timeout": module.timeout,
                    "priority": module.priority,
                    "execution_mode": module.execution_mode,
                    "rate_limit": module.rate_limit
                })
        
        return authorized_modules
        
    except Exception as e:
        logger.error(f"Error getting event-triggered modules: {str(e)}")
        return []

def await_process_event_modules(event_modules: List[Dict[str, Any]], user_id: str, 
                               entity_id: str, message_type: str, event_data: Dict[str, Any],
                               session_id: str) -> List[Dict[str, Any]]:
    """Process event-triggered modules"""
    try:
        results = []
        parallel_modules = []
        
        # Separate modules by execution mode
        for module in event_modules:
            if module["execution_mode"] == "parallel":
                parallel_modules.append(module)
            else:
                # Execute sequential modules immediately
                result = execute_event_module(module, user_id, entity_id, message_type, event_data, session_id)
                results.append(result)
        
        # Execute parallel modules concurrently
        if parallel_modules:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                future_to_module = {
                    executor.submit(execute_event_module, module, user_id, entity_id, message_type, event_data, session_id): module 
                    for module in parallel_modules
                }
                
                for future in concurrent.futures.as_completed(future_to_module):
                    module = future_to_module[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as exc:
                        logger.error(f"Module {module['command']} generated an exception: {exc}")
                        results.append({
                            "module": module["command"],
                            "success": False,
                            "error": str(exc)
                        })
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing event modules: {str(e)}")
        return []

def execute_event_module(module: Dict[str, Any], user_id: str, entity_id: str, 
                        message_type: str, event_data: Dict[str, Any], session_id: str) -> Dict[str, Any]:
    """Execute a single event-triggered module"""
    try:
        # Prepare payload for the module
        payload = {
            "user_id": user_id,
            "entity_id": entity_id,
            "message_type": message_type,
            "event_data": event_data,
            "session_id": session_id,
            "execution_id": f"event_{int(time.time() * 1000000)}",
            "trigger_type": "event"
        }
        
        # Add headers
        headers = {"Content-Type": "application/json"}
        if module.get("headers"):
            headers.update(module["headers"])
        
        # Make request to module
        response = requests.request(
            method=module["method"],
            url=module["location_url"],
            json=payload,
            headers=headers,
            timeout=module["timeout"]
        )
        
        if response.status_code == 200:
            result_data = response.json()
            return {
                "module": module["command"],
                "success": True,
                "response": result_data,
                "status_code": response.status_code,
                "execution_time_ms": response.elapsed.total_seconds() * 1000
            }
        else:
            return {
                "module": module["command"],
                "success": False,
                "error": f"HTTP {response.status_code}",
                "status_code": response.status_code
            }
            
    except requests.RequestException as e:
        logger.error(f"Error executing module {module['command']}: {str(e)}")
        return {
            "module": module["command"],
            "success": False,
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Error executing module {module['command']}: {str(e)}")
        return {
            "module": module["command"],
            "success": False,
            "error": str(e)
        }

@action("router/events", method=["POST"])
@require_api_key(['collector'])
def receive_events():
    """
    Main endpoint for receiving events from collector modules
    Processes messages for commands and routes them appropriately
    """
    try:
        # Parse incoming event data
        event_data = request.json
        if not event_data:
            raise HTTP(400, "No event data provided")
        
        # Validate required fields
        required_fields = ["platform", "server_id", "user_id", "user_name", "message_content", "message_type"]
        missing_fields = [field for field in required_fields if field not in event_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        # Extract event information
        platform = event_data["platform"]
        server_id = event_data["server_id"]
        channel_id = event_data.get("channel_id", "")
        user_id = event_data["user_id"]
        user_name = event_data["user_name"]
        message_content = event_data["message_content"]
        message_type = event_data["message_type"]
        
        # Validate message type
        valid_message_types = [
            "chatMessage", "subscription", "follow", "donation", "cheer", "raid", 
            "host", "subgift", "resub", "reaction", "member_join", "member_leave",
            "voice_join", "voice_leave", "voice_time", "boost", "ban", "kick",
            "timeout", "warn", "file_share", "app_mention", "channel_join"
        ]
        if message_type not in valid_message_types:
            raise HTTP(400, f"Invalid message_type '{message_type}'. Valid types: {', '.join(valid_message_types)}")
        
        # Generate entity ID and ensure it exists in database
        entity_id = command_processor.ensure_entity_exists(platform, server_id, channel_id, user_id)
        session_id = session_manager.create_session(entity_id)
        
        # Ensure user has access to global community with default role
        ensure_user_global_community_access(user_id)
        
        # Process based on message type
        if message_type == "chatMessage":
            # Only chat messages can contain commands
            command_request = command_processor.parse_message(
                message_content=message_content,
                platform=platform,
                server_id=server_id,
                channel_id=channel_id,
                user_id=user_id,
                user_name=user_name
            )
            
            if not command_request:
                # Not a command - check for string matches
                string_match_result = asyncio.run(
                    command_processor.check_string_match(message_content, 
                    command_processor.generate_entity_id(platform, server_id, channel_id))
                )
                
                if string_match_result.matched:
                # Create a dummy request for string match processing
                dummy_request = command_processor.CommandRequest(
                    message_id=f"{platform}_{server_id}_{channel_id}_{int(time.time() * 1000000)}",
                    entity_id=command_processor.generate_entity_id(platform, server_id, channel_id),
                    user_id=user_id,
                    user_name=user_name,
                    command="",
                    parameters=[],
                    raw_message=message_content,
                    platform=platform,
                    server_id=server_id,
                    channel_id=channel_id,
                    timestamp=datetime.utcnow()
                )
                
                result = asyncio.run(
                    command_processor.process_string_match(dummy_request, string_match_result, time.time())
                )
                
                return {
                    "success": result.success,
                    "action": "string_match",
                    "execution_time_ms": result.execution_time_ms,
                    "response": result.response_data,
                    "status_code": result.status_code,
                    "processed": True,
                    "session_id": session_id
                }
            
            # Not a command and no string match - process reputation and check for event-triggered modules
            reputation_result = await_process_reputation_event(
                user_id=user_id,
                entity_id=entity_id,
                message_type=message_type,
                event_data=event_data
            )
            
            # Check for event-triggered modules for chat messages
            event_modules = get_event_triggered_modules(message_type, entity_id)
            module_results = []
            
            if event_modules:
                module_results = await_process_event_modules(
                    event_modules=event_modules,
                    user_id=user_id,
                    entity_id=entity_id,
                    message_type=message_type,
                    event_data=event_data,
                    session_id=session_id
                )
            
            return {
                "success": True,
                "message": "Not a command",
                "processed": False,
                "session_id": session_id,
                "reputation_processed": reputation_result,
                "event_modules_executed": len(module_results),
                "module_results": module_results
            }
        
        # Process the command asynchronously
        result = asyncio.run(command_processor.process_command_async(command_request))
        
        # Also process reputation for chat message commands
        reputation_result = await_process_reputation_event(
            user_id=user_id,
            entity_id=entity_id,
            message_type=message_type,
            event_data=event_data
        )
        
        # Check for event-triggered modules for command messages
        event_modules = get_event_triggered_modules(message_type, entity_id)
        module_results = []
        
        if event_modules:
            module_results = await_process_event_modules(
                event_modules=event_modules,
                user_id=user_id,
                entity_id=entity_id,
                message_type=message_type,
                event_data=event_data,
                session_id=session_id
            )
        
        # Return result
        return {
            "success": result.success,
            "command": command_request.command,
            "execution_time_ms": result.execution_time_ms,
            "response": result.response_data,
            "status_code": result.status_code,
            "processed": True,
            "session_id": session_id,
            "reputation_processed": reputation_result,
            "event_modules_executed": len(module_results),
            "module_results": module_results
        }
        
        else:
            # Non-chat message types - process reputation event and check for event-triggered modules
            reputation_result = await_process_reputation_event(
                user_id=user_id,
                entity_id=entity_id,
                message_type=message_type,
                event_data=event_data
            )
            
            # Check for event-triggered modules
            event_modules = get_event_triggered_modules(message_type, entity_id)
            module_results = []
            
            if event_modules:
                module_results = await_process_event_modules(
                    event_modules=event_modules,
                    user_id=user_id,
                    entity_id=entity_id,
                    message_type=message_type,
                    event_data=event_data,
                    session_id=session_id
                )
            
            return {
                "success": True,
                "message_type": message_type,
                "processed": True,
                "session_id": session_id,
                "reputation_processed": reputation_result,
                "event_modules_executed": len(module_results),
                "module_results": module_results
            }
        
    except Exception as e:
        logger.error(f"Error processing router event: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/events/batch", method=["POST"])
@require_api_key(['collector'])
def receive_events_batch():
    """
    Batch endpoint for processing multiple events efficiently
    """
    try:
        # Parse incoming batch data
        batch_data = request.json
        if not batch_data or "events" not in batch_data:
            raise HTTP(400, "No events provided in batch")
        
        events = batch_data["events"]
        if not isinstance(events, list):
            raise HTTP(400, "Events must be a list")
        
        if len(events) > 100:  # Limit batch size
            raise HTTP(400, "Batch size too large (max 100 events)")
        
        # Parse all events into command requests and ensure global community access
        command_requests = []
        user_ids_to_process = set()
        
        for event_data in events:
            # Validate required fields
            required_fields = ["platform", "server_id", "user_id", "user_name", "message_content"]
            if not all(field in event_data for field in required_fields):
                continue  # Skip invalid events
            
            # Collect user IDs for bulk processing
            user_ids_to_process.add(event_data["user_id"])
            
            # Ensure entity exists in database
            command_processor.ensure_entity_exists(
                platform=event_data["platform"],
                server_id=event_data["server_id"],
                channel_id=event_data.get("channel_id", ""),
                owner=event_data["user_id"]
            )
            
            # Parse command from message
            command_request = command_processor.parse_message(
                message_content=event_data["message_content"],
                platform=event_data["platform"],
                server_id=event_data["server_id"],
                channel_id=event_data.get("channel_id", ""),
                user_id=event_data["user_id"],
                user_name=event_data["user_name"]
            )
            
            if command_request:
                command_requests.append(command_request)
        
        # Bulk ensure global community access for all users
        if user_ids_to_process:
            rbac_service.ensure_users_in_global_community_bulk(list(user_ids_to_process))
        
        if not command_requests:
            return {
                "success": True,
                "message": "No valid commands in batch",
                "processed_count": 0,
                "total_count": len(events)
            }
        
        # Process commands in batch (multi-threaded)
        results = command_processor.process_commands_batch(command_requests)
        
        # Aggregate results
        successful_count = sum(1 for result in results if result.success)
        failed_count = len(results) - successful_count
        avg_execution_time = sum(result.execution_time_ms for result in results) / len(results)
        
        return {
            "success": True,
            "processed_count": len(results),
            "total_count": len(events),
            "successful_count": successful_count,
            "failed_count": failed_count,
            "avg_execution_time_ms": int(avg_execution_time),
            "results": [
                {
                    "command": req.command,
                    "success": result.success,
                    "execution_time_ms": result.execution_time_ms,
                    "status_code": result.status_code
                }
                for req, result in zip(command_requests, results)
            ]
        }
        
    except Exception as e:
        logger.error(f"Error processing batch events: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/commands")
@require_api_key(['collector', 'interaction'])
def list_commands():
    """List available commands"""
    try:
        # Get query parameters
        platform = request.query.get("platform")
        prefix = request.query.get("prefix")
        entity_id = request.query.get("entity_id")
        
        # Build query
        query = (db.commands.is_active == True)
        
        if prefix:
            query &= (db.commands.prefix == prefix)
        
        # Get commands
        commands = db(query).select(
            db.commands.command,
            db.commands.prefix,
            db.commands.description,
            db.commands.location,
            db.commands.type,
            db.commands.module_type,
            db.commands.version,
            orderby=db.commands.command
        )
        
        command_list = []
        for cmd in commands:
            command_info = {
                "command": f"{cmd.prefix}{cmd.command}",
                "description": cmd.description,
                "location": cmd.location,
                "type": cmd.type,
                "module_type": cmd.module_type,
                "version": cmd.version
            }
            
            # If entity_id provided, check if enabled for that entity
            if entity_id:
                entity_record = db(db.entities.entity_id == entity_id).select().first()
                if entity_record:
                    permission = db(
                        (db.command_permissions.command_id == cmd.id) &
                        (db.command_permissions.entity_id == entity_record.id) &
                        (db.command_permissions.is_enabled == True)
                    ).select().first()
                    command_info["enabled"] = permission is not None
            
            command_list.append(command_info)
        
        return {
            "commands": command_list,
            "total": len(command_list)
        }
        
    except Exception as e:
        logger.error(f"Error listing commands: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/entities")
@require_api_key(['collector', 'interaction'])
def list_entities():
    """List registered entities"""
    try:
        entities = db(db.entities.is_active == True).select(
            orderby=db.entities.platform|db.entities.server_id
        )
        
        entity_list = []
        for entity in entities:
            entity_list.append({
                "entity_id": entity.entity_id,
                "platform": entity.platform,
                "server_id": entity.server_id,
                "channel_id": entity.channel_id,
                "owner": entity.owner,
                "created_at": entity.created_at.isoformat()
            })
        
        return {
            "entities": entity_list,
            "total": len(entity_list)
        }
        
    except Exception as e:
        logger.error(f"Error listing entities: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/metrics")
def get_metrics():
    """Get router performance metrics"""
    try:
        # Get processor metrics
        processor_metrics = command_processor.get_metrics()
        
        # Get string matcher metrics
        string_matcher_metrics = command_processor.string_matcher.get_stats()
        
        # Get database metrics
        total_commands = db(db.commands.is_active == True).count()
        total_entities = db(db.entities.is_active == True).count()
        total_executions = db(db.command_executions).count()
        
        # Get recent execution stats
        recent_executions = db(
            db.command_executions.created_at > (datetime.utcnow() - timedelta(hours=1))
        ).select()
        
        recent_successful = sum(1 for exec in recent_executions if exec.status == "success")
        recent_failed = len(recent_executions) - recent_successful
        
        if recent_executions:
            avg_execution_time = sum(exec.execution_time_ms for exec in recent_executions) / len(recent_executions)
        else:
            avg_execution_time = 0
        
        return {
            "processor": processor_metrics,
            "string_matcher": string_matcher_metrics,
            "database": {
                "total_commands": total_commands,
                "total_entities": total_entities,
                "total_executions": total_executions
            },
            "recent_performance": {
                "successful_executions": recent_successful,
                "failed_executions": recent_failed,
                "avg_execution_time_ms": int(avg_execution_time),
                "success_rate": (recent_successful / len(recent_executions)) * 100 if recent_executions else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting metrics: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/health")
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.executesql("SELECT 1")
        
        # Get basic metrics
        processor_metrics = command_processor.get_metrics()
        
        return {
            "status": "healthy",
            "database": "connected",
            "processor": {
                "commands_processed": processor_metrics["commands_processed"],
                "success_rate": (
                    processor_metrics["commands_successful"] / 
                    max(processor_metrics["commands_processed"], 1)
                ) * 100
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        response.status = 503
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@action("router/string-rules", method=["GET", "POST"])
def manage_string_rules():
    """Manage string matching rules"""
    try:
        if request.method == "GET":
            # List string rules
            entity_id = request.query.get("entity_id")
            
            if entity_id:
                # Get rules for specific entity
                rules = db(
                    (db.stringmatch.is_active == True)
                ).select(orderby=db.stringmatch.priority)
                
                # Filter to entity-specific rules
                entity_rules = []
                for rule in rules:
                    enabled_entities = rule.enabled_entity_ids or []
                    if not enabled_entities or entity_id in enabled_entities:
                        entity_rules.append({
                            "id": rule.id,
                            "string": rule.string,
                            "match_type": rule.match_type,
                            "case_sensitive": rule.case_sensitive,
                            "action": rule.action,
                            "priority": rule.priority,
                            "match_count": rule.match_count,
                            "last_matched": rule.last_matched.isoformat() if rule.last_matched else None,
                            "created_at": rule.created_at.isoformat()
                        })
                
                return {
                    "rules": entity_rules,
                    "total": len(entity_rules),
                    "entity_id": entity_id
                }
            else:
                # Get all rules
                rules = db(db.stringmatch.is_active == True).select(orderby=db.stringmatch.priority)
                
                rule_list = []
                for rule in rules:
                    rule_list.append({
                        "id": rule.id,
                        "string": rule.string,
                        "match_type": rule.match_type,
                        "case_sensitive": rule.case_sensitive,
                        "enabled_entity_ids": rule.enabled_entity_ids,
                        "action": rule.action,
                        "command_to_execute": rule.command_to_execute,
                        "command_parameters": rule.command_parameters,
                        "webhook_url": rule.webhook_url,
                        "warning_message": rule.warning_message,
                        "block_message": rule.block_message,
                        "priority": rule.priority,
                        "match_count": rule.match_count,
                        "last_matched": rule.last_matched.isoformat() if rule.last_matched else None,
                        "created_by": rule.created_by,
                        "created_at": rule.created_at.isoformat()
                    })
                
                return {
                    "rules": rule_list,
                    "total": len(rule_list)
                }
        
        elif request.method == "POST":
            # Create new string rule
            rule_data = request.json
            if not rule_data:
                raise HTTP(400, "No rule data provided")
            
            # Validate required fields
            required_fields = ["string", "action"]
            missing_fields = [field for field in required_fields if field not in rule_data]
            if missing_fields:
                raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
            
            # Create the rule
            rule_id = db.stringmatch.insert(
                string=rule_data["string"],
                match_type=rule_data.get("match_type", "exact"),
                case_sensitive=rule_data.get("case_sensitive", False),
                enabled_entity_ids=rule_data.get("enabled_entity_ids", []),
                action=rule_data["action"],
                command_to_execute=rule_data.get("command_to_execute"),
                command_parameters=rule_data.get("command_parameters", []),
                webhook_url=rule_data.get("webhook_url"),
                warning_message=rule_data.get("warning_message"),
                block_message=rule_data.get("block_message"),
                priority=rule_data.get("priority", 100),
                created_by=rule_data.get("created_by", "system")
            )
            db.commit()
            
            # Clear cache for affected entities
            if rule_data.get("enabled_entity_ids"):
                for entity_id in rule_data["enabled_entity_ids"]:
                    command_processor.string_matcher.clear_cache(entity_id)
            
            return {
                "success": True,
                "rule_id": rule_id,
                "message": "String rule created successfully"
            }
            
    except Exception as e:
        logger.error(f"Error managing string rules: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/string-rules/<rule_id:int>", method=["PUT", "DELETE"])
def manage_string_rule(rule_id):
    """Manage individual string rule"""
    try:
        if request.method == "PUT":
            # Update string rule
            rule_data = request.json
            if not rule_data:
                raise HTTP(400, "No rule data provided")
            
            # Check if rule exists
            rule = db(db.stringmatch.id == rule_id).select().first()
            if not rule:
                raise HTTP(404, "String rule not found")
            
            # Update the rule
            update_data = {}
            updatable_fields = [
                "string", "match_type", "case_sensitive", "enabled_entity_ids", 
                "action", "command_to_execute", "command_parameters", "webhook_url",
                "warning_message", "block_message", "priority", "is_active"
            ]
            
            for field in updatable_fields:
                if field in rule_data:
                    update_data[field] = rule_data[field]
            
            if update_data:
                db.stringmatch[rule_id] = update_data
                db.commit()
                
                # Clear cache for affected entities
                old_entities = rule.enabled_entity_ids or []
                new_entities = rule_data.get("enabled_entity_ids", old_entities)
                
                affected_entities = set(old_entities + new_entities)
                for entity_id in affected_entities:
                    command_processor.string_matcher.clear_cache(entity_id)
            
            return {
                "success": True,
                "message": "String rule updated successfully"
            }
        
        elif request.method == "DELETE":
            # Delete string rule (soft delete)
            rule = db(db.stringmatch.id == rule_id).select().first()
            if not rule:
                raise HTTP(404, "String rule not found")
            
            db.stringmatch[rule_id] = dict(is_active=False)
            db.commit()
            
            # Clear cache for affected entities
            if rule.enabled_entity_ids:
                for entity_id in rule.enabled_entity_ids:
                    command_processor.string_matcher.clear_cache(entity_id)
            
            return {
                "success": True,
                "message": "String rule deleted successfully"
            }
            
    except Exception as e:
        logger.error(f"Error managing string rule {rule_id}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/responses", method=["POST"])
@require_api_key(['interaction', 'webhook'])
def submit_module_response():
    """Submit response from interaction module or webhook"""
    try:
        response_data = request.json
        if not response_data:
            raise HTTP(400, "No response data provided")
        
        # Validate required fields
        required_fields = ["execution_id", "module_name", "success", "response_action", "session_id"]
        missing_fields = [field for field in required_fields if field not in response_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate response_action
        valid_actions = ["chat", "media", "ticker", "form"]
        if response_data["response_action"] not in valid_actions:
            raise HTTP(400, f"Invalid response_action. Must be one of: {', '.join(valid_actions)}")
        
        # Validate execution_id exists
        execution = db(db.command_executions.execution_id == response_data["execution_id"]).select().first()
        if not execution:
            raise HTTP(404, f"Execution ID {response_data['execution_id']} not found")
        
        # Validate session_id exists and get entity_id
        session_id = response_data["session_id"]
        entity_id = session_manager.get_entity_id(session_id)
        if not entity_id:
            raise HTTP(404, f"Session ID {session_id} not found or expired")
        
        # Validate that session belongs to the entity from the execution
        if not session_manager.validate_session(session_id, execution.entity_id):
            raise HTTP(403, f"Session ID {session_id} does not match execution entity")
        
        # Update session activity
        session_manager.update_session_activity(session_id)
        
        # Process response based on action type
        response_record = {
            "execution_id": response_data["execution_id"],
            "module_name": response_data["module_name"],
            "success": response_data["success"],
            "response_action": response_data["response_action"],
            "response_data": response_data.get("response_data", {}),
            "error_message": response_data.get("error_message"),
            "processing_time_ms": response_data.get("processing_time_ms", 0)
        }
        
        # Add action-specific fields
        if response_data["response_action"] == "chat":
            response_record["chat_message"] = response_data.get("chat_message", "")
            
        elif response_data["response_action"] == "media":
            response_record["media_type"] = response_data.get("media_type", "")
            response_record["media_url"] = response_data.get("media_url", "")
            
        elif response_data["response_action"] == "ticker":
            response_record["ticker_text"] = response_data.get("ticker_text", "")
            response_record["ticker_duration"] = response_data.get("ticker_duration", 10)
            
        elif response_data["response_action"] == "form":
            response_record["form_title"] = response_data.get("form_title", "")
            response_record["form_description"] = response_data.get("form_description", "")
            response_record["form_fields"] = response_data.get("form_fields", [])
            response_record["form_submit_url"] = response_data.get("form_submit_url", "")
            response_record["form_submit_method"] = response_data.get("form_submit_method", "POST")
            response_record["form_callback_url"] = response_data.get("form_callback_url", "")
        
        # Insert response record
        response_id = db.module_responses.insert(**response_record)
        db.commit()
        
        return {
            "success": True,
            "response_id": response_id,
            "message": "Module response recorded successfully"
        }
        
    except Exception as e:
        logger.error(f"Error submitting module response: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/responses/<execution_id>", method=["GET"])
def get_module_responses(execution_id):
    """Get responses for a specific execution"""
    try:
        # Get all responses for this execution
        responses = db(db.module_responses.execution_id == execution_id).select(
            orderby=db.module_responses.created_at
        )
        
        response_list = []
        for resp in responses:
            response_info = {
                "id": resp.id,
                "module_name": resp.module_name,
                "success": resp.success,
                "response_action": resp.response_action,
                "response_data": resp.response_data,
                "processing_time_ms": resp.processing_time_ms,
                "created_at": resp.created_at.isoformat()
            }
            
            # Add action-specific fields
            if resp.response_action == "chat":
                response_info["chat_message"] = resp.chat_message
            elif resp.response_action == "media":
                response_info["media_type"] = resp.media_type
                response_info["media_url"] = resp.media_url
            elif resp.response_action == "ticker":
                response_info["ticker_text"] = resp.ticker_text
                response_info["ticker_duration"] = resp.ticker_duration
            elif resp.response_action == "form":
                response_info["form_title"] = resp.form_title
                response_info["form_description"] = resp.form_description
                response_info["form_fields"] = resp.form_fields
                response_info["form_submit_url"] = resp.form_submit_url
                response_info["form_submit_method"] = resp.form_submit_method
                response_info["form_callback_url"] = resp.form_callback_url
            
            if resp.error_message:
                response_info["error_message"] = resp.error_message
                
            response_list.append(response_info)
        
        return {
            "execution_id": execution_id,
            "responses": response_list,
            "total": len(response_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting module responses for {execution_id}: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/responses/recent", method=["GET"])
def get_recent_responses():
    """Get recent module responses with filtering"""
    try:
        # Get query parameters
        module_name = request.query.get("module_name")
        response_action = request.query.get("response_action")
        success_only = request.query.get("success_only", "false").lower() == "true"
        limit = int(request.query.get("limit", 50))
        
        # Build query
        query = (db.module_responses.id > 0)  # Base query
        
        if module_name:
            query &= (db.module_responses.module_name == module_name)
        
        if response_action:
            query &= (db.module_responses.response_action == response_action)
        
        if success_only:
            query &= (db.module_responses.success == True)
        
        # Get responses
        responses = db(query).select(
            orderby=~db.module_responses.created_at,
            limitby=(0, limit)
        )
        
        response_list = []
        for resp in responses:
            response_info = {
                "id": resp.id,
                "execution_id": resp.execution_id,
                "module_name": resp.module_name,
                "success": resp.success,
                "response_action": resp.response_action,
                "processing_time_ms": resp.processing_time_ms,
                "created_at": resp.created_at.isoformat()
            }
            
            # Add action-specific fields based on type
            if resp.response_action == "chat" and resp.chat_message:
                response_info["chat_message"] = resp.chat_message[:100] + "..." if len(resp.chat_message) > 100 else resp.chat_message
            elif resp.response_action == "media":
                response_info["media_type"] = resp.media_type
                response_info["media_url"] = resp.media_url
            elif resp.response_action == "ticker":
                response_info["ticker_text"] = resp.ticker_text[:50] + "..." if len(resp.ticker_text or "") > 50 else resp.ticker_text
                response_info["ticker_duration"] = resp.ticker_duration
            elif resp.response_action == "form":
                response_info["form_title"] = resp.form_title
                response_info["form_description"] = resp.form_description[:100] + "..." if len(resp.form_description or "") > 100 else resp.form_description
                response_info["form_fields_count"] = len(resp.form_fields) if resp.form_fields else 0
                response_info["form_submit_url"] = resp.form_submit_url
                response_info["form_submit_method"] = resp.form_submit_method
            
            response_list.append(response_info)
        
        return {
            "responses": response_list,
            "total": len(response_list),
            "filters": {
                "module_name": module_name,
                "response_action": response_action,
                "success_only": success_only,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting recent responses: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/claim", method=["POST"])
@require_api_key(['collector'])
def claim_entities():
    """Claim available entities for a collector container"""
    try:
        claim_data = request.json or {}
        
        # Get parameters
        platform = claim_data.get("platform")
        container_id = claim_data.get("container_id")
        max_claims = claim_data.get("max_claims", 5)
        
        if not platform:
            raise HTTP(400, "Platform is required")
        
        if not container_id:
            raise HTTP(400, "Container ID is required")
        
        # Import coordination manager here to avoid circular imports
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id, max_claims)
        result = asyncio.run(coord_manager.claim_entities(platform, max_claims))
        
        return {
            "success": result.success,
            "claimed_entities": result.claimed_entities,
            "claimed_count": len(result.claimed_entities),
            "container_id": container_id,
            "platform": platform,
            "error_message": result.error_message
        }
        
    except Exception as e:
        logger.error(f"Error claiming entities: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/release", method=["POST"])
@require_api_key(['collector'])
def release_entities():
    """Release claimed entities"""
    try:
        release_data = request.json or {}
        
        container_id = release_data.get("container_id")
        entity_ids = release_data.get("entity_ids")  # Optional: specific entities to release
        
        if not container_id:
            raise HTTP(400, "Container ID is required")
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id)
        success = asyncio.run(coord_manager.release_entities(entity_ids))
        
        return {
            "success": success,
            "container_id": container_id,
            "released_entities": entity_ids or "all"
        }
        
    except Exception as e:
        logger.error(f"Error releasing entities: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/checkin", method=["POST"])
@require_api_key(['collector'])
def coordination_checkin():
    """Container checkin to maintain claims"""
    try:
        checkin_data = request.json or {}
        
        container_id = checkin_data.get("container_id")
        
        if not container_id:
            raise HTTP(400, "Container ID is required")
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id)
        success = asyncio.run(coord_manager.checkin())
        
        return {
            "success": success,
            "container_id": container_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing checkin: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/heartbeat", method=["POST"])
def coordination_heartbeat():
    """Send heartbeat and extend claims"""
    try:
        heartbeat_data = request.json or {}
        
        container_id = heartbeat_data.get("container_id")
        extend_claims = heartbeat_data.get("extend_claims", True)
        
        if not container_id:
            raise HTTP(400, "Container ID is required")
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id)
        result = asyncio.run(coord_manager.heartbeat(extend_claims))
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing heartbeat: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/release-offline", method=["POST"])
def release_offline_entities():
    """Release offline entities and claim new ones"""
    try:
        release_data = request.json or {}
        
        container_id = release_data.get("container_id")
        
        if not container_id:
            raise HTTP(400, "Container ID is required")
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id)
        released_entities = asyncio.run(coord_manager.release_offline_entities())
        
        return {
            "success": True,
            "container_id": container_id,
            "released_entities": released_entities,
            "released_count": len(released_entities)
        }
        
    except Exception as e:
        logger.error(f"Error releasing offline entities: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/status", method=["POST"])
def update_entity_status():
    """Update status of claimed entity"""
    try:
        status_data = request.json
        if not status_data:
            raise HTTP(400, "Status data is required")
        
        # Validate required fields
        required_fields = ["container_id", "entity_id"]
        missing_fields = [field for field in required_fields if field not in status_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        container_id = status_data["container_id"]
        entity_id = status_data["entity_id"]
        is_live = status_data.get("is_live")
        viewer_count = status_data.get("viewer_count")
        metadata = status_data.get("metadata")
        has_activity = status_data.get("has_activity", False)
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id)
        success = asyncio.run(coord_manager.update_entity_status(
            entity_id=entity_id,
            is_live=is_live,
            viewer_count=viewer_count,
            metadata=metadata,
            has_activity=has_activity
        ))
        
        return {
            "success": success,
            "entity_id": entity_id,
            "container_id": container_id
        }
        
    except Exception as e:
        logger.error(f"Error updating entity status: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/error", method=["POST"])
def report_entity_error():
    """Report error for an entity"""
    try:
        error_data = request.json
        if not error_data:
            raise HTTP(400, "Error data is required")
        
        # Validate required fields
        required_fields = ["container_id", "entity_id", "error_message"]
        missing_fields = [field for field in required_fields if field not in error_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        container_id = error_data["container_id"]
        entity_id = error_data["entity_id"]
        error_message = error_data["error_message"]
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager(container_id)
        success = asyncio.run(coord_manager.report_error(entity_id, error_message))
        
        return {
            "success": success,
            "entity_id": entity_id,
            "container_id": container_id,
            "error_message": error_message
        }
        
    except Exception as e:
        logger.error(f"Error reporting entity error: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/stats", method=["GET"])
def get_coordination_stats():
    """Get coordination system statistics"""
    try:
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager()
        stats = coord_manager.get_stats()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting coordination stats: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/entities", method=["GET"])
def list_coordination_entities():
    """List entities in coordination table with filtering"""
    try:
        # Get query parameters
        platform = request.query.get("platform")
        status = request.query.get("status")
        claimed_by = request.query.get("claimed_by")
        is_live = request.query.get("is_live")
        limit = int(request.query.get("limit", 100))
        
        # Build query
        query = (db.coordination.id > 0)
        
        if platform:
            query &= (db.coordination.platform == platform)
        
        if status:
            query &= (db.coordination.status == status)
        
        if claimed_by:
            query &= (db.coordination.claimed_by == claimed_by)
        
        if is_live is not None:
            query &= (db.coordination.is_live == (is_live.lower() == "true"))
        
        # Get entities
        entities = db(query).select(
            orderby=(~db.coordination.is_live, 
                    db.coordination.platform, 
                    db.coordination.priority),
            limitby=(0, limit)
        )
        
        entity_list = []
        for entity in entities:
            entity_info = {
                "id": entity.id,
                "platform": entity.platform,
                "server_id": entity.server_id,
                "channel_id": entity.channel_id,
                "entity_id": entity.entity_id,
                "claimed_by": entity.claimed_by,
                "claimed_at": entity.claimed_at.isoformat() if entity.claimed_at else None,
                "status": entity.status,
                "is_live": entity.is_live,
                "viewer_count": entity.viewer_count,
                "last_activity": entity.last_activity.isoformat() if entity.last_activity else None,
                "last_check": entity.last_check.isoformat() if entity.last_check else None,
                "claim_expires": entity.claim_expires.isoformat() if entity.claim_expires else None,
                "error_count": entity.error_count,
                "priority": entity.priority,
                "created_at": entity.created_at.isoformat()
            }
            entity_list.append(entity_info)
        
        return {
            "entities": entity_list,
            "total": len(entity_list),
            "filters": {
                "platform": platform,
                "status": status,
                "claimed_by": claimed_by,
                "is_live": is_live,
                "limit": limit
            }
        }
        
    except Exception as e:
        logger.error(f"Error listing coordination entities: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("router/coordination/populate", method=["POST"])
def populate_coordination_table():
    """Populate coordination table from servers table"""
    try:
        populate_data = request.json or {}
        platform = populate_data.get("platform")
        
        if not platform:
            raise HTTP(400, "Platform is required")
        
        from ..services.coordination_manager import get_coordination_manager
        
        coord_manager = get_coordination_manager()
        count = asyncio.run(coord_manager.populate_from_servers_table(platform))
        
        return {
            "success": True,
            "platform": platform,
            "entities_added": count
        }
        
    except Exception as e:
        logger.error(f"Error populating coordination table: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")