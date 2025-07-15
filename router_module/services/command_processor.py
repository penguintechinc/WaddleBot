"""
High-performance command processor with multi-threading and caching
Handles command lookup, validation, and execution routing
"""

import asyncio
import logging
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import json
import requests
from dataclasses import dataclass

from ..models import db, db_read
from ..config import load_config, COMMAND_PREFIXES
from .cache_manager import CacheManager
from .rate_limiter import RateLimiter
from .execution_engine import ExecutionEngine
from .string_matcher import get_string_matcher, StringMatchResult

logger = logging.getLogger(__name__)

# Load configuration
router_config, lambda_config, openwhisk_config, waddlebot_config = load_config()

@dataclass
class CommandRequest:
    """Command request data structure"""
    message_id: str
    entity_id: str
    user_id: str
    user_name: str
    command: str
    parameters: List[str]
    raw_message: str
    platform: str
    server_id: str
    channel_id: str
    timestamp: datetime
    
@dataclass 
class CommandResult:
    """Command execution result"""
    success: bool
    response_data: Any
    execution_time_ms: int
    status_code: int = 200
    error_message: str = None
    retry_count: int = 0

class CommandProcessor:
    """High-performance command processor with multi-threading"""
    
    def __init__(self):
        self.cache_manager = CacheManager(
            command_ttl=router_config.command_cache_ttl,
            entity_ttl=router_config.entity_cache_ttl
        )
        self.rate_limiter = RateLimiter(
            default_limit=router_config.default_rate_limit,
            window_seconds=router_config.rate_limit_window
        )
        self.execution_engine = ExecutionEngine(
            lambda_config=lambda_config,
            openwhisk_config=openwhisk_config,
            timeout=router_config.request_timeout,
            max_retries=router_config.max_retries
        )
        
        # Thread pool for concurrent processing
        self.thread_pool = ThreadPoolExecutor(
            max_workers=router_config.max_workers,
            thread_name_prefix="CommandProcessor"
        )
        
        # String matcher for content moderation
        self.string_matcher = get_string_matcher(self.cache_manager)
        
        # Metrics tracking
        self.metrics_lock = Lock()
        self.metrics = {
            "commands_processed": 0,
            "commands_successful": 0,
            "commands_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "rate_limits_hit": 0,
            "string_matches": 0,
            "avg_execution_time": 0.0
        }
        
        logger.info("CommandProcessor initialized with {} workers".format(router_config.max_workers))
    
    def parse_message(self, message_content: str, platform: str, server_id: str, 
                     channel_id: str, user_id: str, user_name: str) -> Optional[CommandRequest]:
        """Parse message to extract command and parameters"""
        
        if not message_content or len(message_content) < 2:
            return None
        
        # Check for command prefixes
        prefix = message_content[0]
        if prefix not in COMMAND_PREFIXES:
            return None
        
        # Parse command and parameters
        parts = message_content[1:].strip().split()
        if not parts:
            return None
        
        command = parts[0].lower()
        parameters = parts[1:] if len(parts) > 1 else []
        
        # Generate entity ID
        entity_id = self.generate_entity_id(platform, server_id, channel_id)
        
        return CommandRequest(
            message_id=f"{platform}_{server_id}_{channel_id}_{int(time.time() * 1000000)}",
            entity_id=entity_id,
            user_id=user_id,
            user_name=user_name,
            command=command,
            parameters=parameters,
            raw_message=message_content,
            platform=platform,
            server_id=server_id,
            channel_id=channel_id,
            timestamp=datetime.utcnow()
        )
    
    def generate_entity_id(self, platform: str, server_id: str, channel_id: str = None) -> str:
        """Generate unique entity ID for platform+server+channel combination"""
        # New format: platform+server+channel (using + instead of :)
        if platform == "twitch":
            # Twitch doesn't have sub-channels, so just platform+channel
            return f"{platform}+{server_id}"
        elif platform in ["discord", "slack"]:
            # Discord/Slack have servers and channels
            if channel_id:
                return f"{platform}+{server_id}+{channel_id}"
            else:
                # Server-wide entity (default channel)
                return f"{platform}+{server_id}"
        else:
            # Generic format for other platforms
            if channel_id:
                return f"{platform}+{server_id}+{channel_id}"
            else:
                return f"{platform}+{server_id}"
    
    def ensure_entity_exists(self, platform: str, server_id: str, channel_id: str = None, 
                            owner: str = None) -> str:
        """Ensure entity exists in database and return entity_id"""
        try:
            entity_id = self.generate_entity_id(platform, server_id, channel_id)
            
            # Check if entity already exists
            existing_entity = db(db.entities.entity_id == entity_id).select().first()
            
            if not existing_entity:
                # Create new entity
                db.entities.insert(
                    entity_id=entity_id,
                    platform=platform,
                    server_id=server_id,
                    channel_id=channel_id or "",
                    owner=owner or "system",
                    is_active=True,
                    config={}
                )
                db.commit()
                logger.info(f"Created new entity: {entity_id}")
                
                # Auto-create server-wide entity group if this is a Discord/Slack server
                if platform in ["discord", "slack"] and not channel_id:
                    self.create_server_entity_group(platform, server_id, entity_id, owner)
            
            return entity_id
            
        except Exception as e:
            logger.error(f"Error ensuring entity exists: {str(e)}")
            return entity_id
    
    def create_server_entity_group(self, platform: str, server_id: str, 
                                  default_entity_id: str, owner: str = None) -> None:
        """Create server-wide entity group for Discord/Slack servers"""
        try:
            # Check if entity group already exists
            existing_group = db(
                (db.entity_groups.platform == platform) &
                (db.entity_groups.server_id == server_id)
            ).select().first()
            
            if not existing_group:
                # Create entity group
                group_id = db.entity_groups.insert(
                    name=f"{platform.title()} Server {server_id}",
                    platform=platform,
                    server_id=server_id,
                    entity_ids=[default_entity_id],
                    community_id=None,  # Will be assigned when added to community
                    is_active=True,
                    created_by=owner or "system"
                )
                
                # Create default entity mapping
                db.entity_defaults.insert(
                    entity_group_id=group_id,
                    default_entity_id=default_entity_id,
                    is_active=True
                )
                
                db.commit()
                logger.info(f"Created entity group for {platform} server {server_id}")
                
        except Exception as e:
            logger.error(f"Error creating server entity group: {str(e)}")
    
    async def process_command_async(self, request: CommandRequest) -> CommandResult:
        """Process a single command asynchronously"""
        start_time = time.time()
        
        try:
            # 1. Look up command definition
            command_def = await self.lookup_command(request.command, request.raw_message[0])
            if not command_def:
                # No command found - check for string matches
                string_match_result = await self.check_string_match(request.raw_message, request.entity_id)
                if string_match_result.matched:
                    return await self.process_string_match(request, string_match_result, start_time)
                
                return CommandResult(
                    success=False,
                    response_data={"error": f"Command '{request.command}' not found"},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    status_code=404,
                    error_message=f"Command not found: {request.command}"
                )
            
            # 2. Check if entity has permission for this command
            has_permission = await self.check_command_permission(command_def['id'], request.entity_id)
            if not has_permission:
                return CommandResult(
                    success=False,
                    response_data={"error": f"Command '{request.command}' not enabled for this channel"},
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    status_code=403,
                    error_message="Command not enabled"
                )
            
            # 3. Check rate limits
            if command_def.get('rate_limit', 0) > 0:
                rate_ok = await self.rate_limiter.check_rate_limit(
                    command_def['id'], 
                    request.entity_id, 
                    request.user_id,
                    command_def['rate_limit']
                )
                if not rate_ok:
                    with self.metrics_lock:
                        self.metrics["rate_limits_hit"] += 1
                    
                    return CommandResult(
                        success=False,
                        response_data={"error": "Rate limit exceeded"},
                        execution_time_ms=int((time.time() - start_time) * 1000),
                        status_code=429,
                        error_message="Rate limit exceeded"
                    )
            
            # 4. Execute command
            execution_result = await self.execution_engine.execute_command(
                command_def=command_def,
                request=request
            )
            
            # 5. Log execution
            await self.log_execution(request, command_def, execution_result)
            
            # 6. Update metrics
            execution_time = int((time.time() - start_time) * 1000)
            with self.metrics_lock:
                self.metrics["commands_processed"] += 1
                if execution_result.success:
                    self.metrics["commands_successful"] += 1
                else:
                    self.metrics["commands_failed"] += 1
                
                # Update average execution time
                total_commands = self.metrics["commands_processed"]
                current_avg = self.metrics["avg_execution_time"]
                self.metrics["avg_execution_time"] = (
                    (current_avg * (total_commands - 1) + execution_time) / total_commands
                )
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error processing command {request.command}: {str(e)}")
            return CommandResult(
                success=False,
                response_data={"error": "Internal server error"},
                execution_time_ms=int((time.time() - start_time) * 1000),
                status_code=500,
                error_message=str(e)
            )
    
    async def lookup_command(self, command: str, prefix: str) -> Optional[Dict]:
        """Look up command definition with caching"""
        cache_key = f"command:{prefix}:{command}"
        
        # Try cache first
        cached_command = self.cache_manager.get(cache_key)
        if cached_command:
            with self.metrics_lock:
                self.metrics["cache_hits"] += 1
            return cached_command
        
        # Cache miss - query database (read replica)
        with self.metrics_lock:
            self.metrics["cache_misses"] += 1
        
        try:
            command_record = db_read(
                (db_read.commands.command == command) &
                (db_read.commands.prefix == prefix) &
                (db_read.commands.is_active == True)
            ).select().first()
            
            if command_record:
                command_dict = dict(command_record)
                # Cache the result
                self.cache_manager.set(cache_key, command_dict)
                return command_dict
            
            return None
            
        except Exception as e:
            logger.error(f"Error looking up command {command}: {str(e)}")
            return None
    
    async def check_command_permission(self, command_id: int, entity_id: str) -> bool:
        """Check if entity has permission to use command"""
        cache_key = f"permission:{command_id}:{entity_id}"
        
        # Try cache first
        cached_permission = self.cache_manager.get(cache_key)
        if cached_permission is not None:
            return cached_permission
        
        try:
            # Get entity record
            entity_record = db_read(db_read.entities.entity_id == entity_id).select().first()
            if not entity_record:
                # Entity not found - cache negative result briefly
                self.cache_manager.set(cache_key, False, ttl=60)
                return False
            
            # Check permission
            permission_record = db_read(
                (db_read.command_permissions.command_id == command_id) &
                (db_read.command_permissions.entity_id == entity_record.id) &
                (db_read.command_permissions.is_enabled == True)
            ).select().first()
            
            has_permission = permission_record is not None
            
            # Cache the result
            self.cache_manager.set(cache_key, has_permission, ttl=300)
            return has_permission
            
        except Exception as e:
            logger.error(f"Error checking command permission: {str(e)}")
            return False
    
    async def log_execution(self, request: CommandRequest, command_def: Dict, result: CommandResult):
        """Log command execution to database"""
        try:
            # Get entity record for foreign key
            entity_record = db_read(db_read.entities.entity_id == request.entity_id).select().first()
            entity_ref_id = entity_record.id if entity_record else None
            
            db.command_executions.insert(
                execution_id=request.message_id,
                command_id=command_def['id'],
                entity_id=entity_ref_id,
                user_id=request.user_id,
                user_name=request.user_name,
                message_content=request.raw_message,
                parameters=request.parameters,
                location_url=command_def.get('location_url'),
                request_payload={
                    "command": request.command,
                    "parameters": request.parameters,
                    "user": request.user_name,
                    "entity_id": request.entity_id,
                    "platform": request.platform
                },
                response_status=result.status_code,
                response_data=result.response_data,
                execution_time_ms=result.execution_time_ms,
                error_message=result.error_message,
                retry_count=result.retry_count,
                status="success" if result.success else "failed",
                completed_at=datetime.utcnow()
            )
            db.commit()
            
            # Update usage count
            if entity_ref_id:
                permission_record = db(
                    (db.command_permissions.command_id == command_def['id']) &
                    (db.command_permissions.entity_id == entity_ref_id)
                ).select().first()
                
                if permission_record:
                    db.command_permissions[permission_record.id] = dict(
                        usage_count=permission_record.usage_count + 1,
                        last_used=datetime.utcnow()
                    )
                    db.commit()
                    
        except Exception as e:
            logger.error(f"Error logging execution: {str(e)}")
    
    async def check_string_match(self, message_content: str, entity_id: str) -> StringMatchResult:
        """Check if message matches any string patterns"""
        try:
            return await self.string_matcher.check_string_match(message_content, entity_id)
        except Exception as e:
            logger.error(f"Error checking string match: {str(e)}")
            return StringMatchResult(matched=False)
    
    async def process_string_match(self, request: CommandRequest, match_result: StringMatchResult, start_time: float) -> CommandResult:
        """Process a string match result"""
        try:
            # Update metrics
            with self.metrics_lock:
                self.metrics["string_matches"] += 1
            
            execution_time = int((time.time() - start_time) * 1000)
            
            if match_result.action == 'warn':
                return CommandResult(
                    success=True,
                    response_data={
                        "action": "warn",
                        "message": match_result.message,
                        "rule_id": match_result.rule_id
                    },
                    execution_time_ms=execution_time,
                    status_code=200
                )
            
            elif match_result.action == 'block':
                return CommandResult(
                    success=True,
                    response_data={
                        "action": "block",
                        "message": match_result.message,
                        "rule_id": match_result.rule_id
                    },
                    execution_time_ms=execution_time,
                    status_code=200
                )
            
            elif match_result.action == 'command':
                # Execute the specified command
                if match_result.command_to_execute:
                    # Create new command request for the triggered command
                    triggered_request = CommandRequest(
                        message_id=f"{request.message_id}_triggered",
                        entity_id=request.entity_id,
                        user_id=request.user_id,
                        user_name=request.user_name,
                        command=match_result.command_to_execute,
                        parameters=match_result.command_parameters or [],
                        raw_message=f"#{match_result.command_to_execute}" + (" " + " ".join(match_result.command_parameters) if match_result.command_parameters else ""),
                        platform=request.platform,
                        server_id=request.server_id,
                        channel_id=request.channel_id,
                        timestamp=request.timestamp
                    )
                    
                    # Process the triggered command
                    triggered_result = await self.process_command_async(triggered_request)
                    
                    return CommandResult(
                        success=triggered_result.success,
                        response_data={
                            "action": "command",
                            "triggered_command": match_result.command_to_execute,
                            "command_result": triggered_result.response_data,
                            "rule_id": match_result.rule_id
                        },
                        execution_time_ms=execution_time + triggered_result.execution_time_ms,
                        status_code=triggered_result.status_code
                    )
                else:
                    return CommandResult(
                        success=False,
                        response_data={
                            "action": "command",
                            "error": "No command specified for execution",
                            "rule_id": match_result.rule_id
                        },
                        execution_time_ms=execution_time,
                        status_code=500
                    )
            
            elif match_result.action == 'webhook':
                # Execute webhook action
                webhook_result = await self.execute_string_match_webhook(request, match_result)
                
                return CommandResult(
                    success=webhook_result.get('success', False),
                    response_data={
                        "action": "webhook",
                        "webhook_result": webhook_result,
                        "rule_id": match_result.rule_id
                    },
                    execution_time_ms=execution_time,
                    status_code=webhook_result.get('status_code', 200)
                )
            
            else:
                return CommandResult(
                    success=True,
                    response_data={
                        "action": match_result.action,
                        "message": match_result.message,
                        "rule_id": match_result.rule_id
                    },
                    execution_time_ms=execution_time,
                    status_code=200
                )
                
        except Exception as e:
            logger.error(f"Error processing string match: {str(e)}")
            execution_time = int((time.time() - start_time) * 1000)
            return CommandResult(
                success=False,
                response_data={"error": "String match processing failed"},
                execution_time_ms=execution_time,
                status_code=500,
                error_message=str(e)
            )
    
    async def execute_string_match_webhook(self, request: CommandRequest, match_result: StringMatchResult) -> Dict:
        """Execute webhook for string match"""
        try:
            # Get webhook URL from string match rule
            rule = db_read(db_read.stringmatch.id == match_result.rule_id).select().first()
            if not rule or not rule.webhook_url:
                return {"success": False, "error": "No webhook URL configured", "status_code": 500}
            
            # Prepare webhook payload
            payload = {
                "type": "string_match",
                "rule_id": match_result.rule_id,
                "pattern": rule.string,
                "match_type": rule.match_type,
                "message_content": request.raw_message,
                "user": {
                    "id": request.user_id,
                    "name": request.user_name
                },
                "context": {
                    "platform": request.platform,
                    "server_id": request.server_id,
                    "channel_id": request.channel_id,
                    "entity_id": request.entity_id,
                    "message_id": request.message_id,
                    "timestamp": request.timestamp.isoformat()
                }
            }
            
            # Execute webhook using execution engine
            session = await self.execution_engine.get_session()
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WaddleBot-Router/1.0',
                'X-WaddleBot-Source': 'string-matcher',
                'X-WaddleBot-Type': 'string-match-webhook'
            }
            
            async with session.post(
                rule.webhook_url,
                json=payload,
                headers=headers
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = {"response": await response.text()}
                
                return {
                    "success": 200 <= response.status < 300,
                    "response_data": response_data,
                    "status_code": response.status,
                    "webhook_url": rule.webhook_url
                }
                
        except Exception as e:
            logger.error(f"Error executing string match webhook: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "status_code": 500
            }
    
    def process_commands_batch(self, requests: List[CommandRequest]) -> List[CommandResult]:
        """Process multiple commands concurrently"""
        if not requests:
            return []
        
        logger.info(f"Processing batch of {len(requests)} commands")
        
        # Submit all tasks to thread pool
        future_to_request = {}
        for request in requests:
            future = self.thread_pool.submit(
                asyncio.run, 
                self.process_command_async(request)
            )
            future_to_request[future] = request
        
        # Collect results as they complete
        results = []
        for future in as_completed(future_to_request.keys(), timeout=router_config.request_timeout + 10):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                request = future_to_request[future]
                logger.error(f"Error processing command {request.command}: {str(e)}")
                results.append(CommandResult(
                    success=False,
                    response_data={"error": "Processing failed"},
                    execution_time_ms=0,
                    status_code=500,
                    error_message=str(e)
                ))
        
        return results
    
    def get_metrics(self) -> Dict:
        """Get current metrics"""
        with self.metrics_lock:
            return self.metrics.copy()
    
    def shutdown(self):
        """Shutdown the processor"""
        logger.info("Shutting down CommandProcessor...")
        self.thread_pool.shutdown(wait=True)
        logger.info("CommandProcessor shutdown complete")

# Global processor instance
command_processor = CommandProcessor()