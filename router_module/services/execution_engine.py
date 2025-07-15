"""
Command execution engine for Lambda, OpenWhisk, and webhook endpoints
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..config import LambdaConfig, OpenWhiskConfig

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Command execution result"""
    success: bool
    response_data: Any
    execution_time_ms: int
    status_code: int = 200
    error_message: str = None
    retry_count: int = 0

class ExecutionEngine:
    """Multi-platform command execution engine"""
    
    def __init__(self, lambda_config: LambdaConfig, openwhisk_config: OpenWhiskConfig, 
                 timeout: int = 30, max_retries: int = 3):
        self.lambda_config = lambda_config
        self.openwhisk_config = openwhisk_config
        self.timeout = timeout
        self.max_retries = max_retries
        
        # HTTP session for connections
        self.session = None
    
    async def get_session(self):
        """Get or create HTTP session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def execute_command(self, command_def: Dict, request, user_context: Dict = None) -> ExecutionResult:
        """Execute command based on type and location"""
        command_type = command_def.get('type', 'lambda')  # container, lambda, openwhisk, webhook
        location = command_def.get('location', 'community')  # internal, community
        location_url = command_def.get('location_url')
        
        if not location_url:
            return ExecutionResult(
                success=False,
                response_data={"error": "No location URL configured"},
                execution_time_ms=0,
                status_code=500,
                error_message="Missing location URL"
            )
        
        start_time = time.time()
        
        try:
            if command_type == 'container':
                result = await self._execute_container(command_def, request, user_context)
            elif command_type == 'lambda':
                result = await self._execute_lambda(command_def, request, user_context)
            elif command_type == 'openwhisk':
                result = await self._execute_openwhisk(command_def, request, user_context)
            elif command_type == 'webhook':
                result = await self._execute_webhook(command_def, request, user_context)
            else:
                result = ExecutionResult(
                    success=False,
                    response_data={"error": f"Unsupported command type: {command_type}"},
                    execution_time_ms=0,
                    status_code=500,
                    error_message=f"Unsupported command type: {command_type}"
                )
            
            execution_time = int((time.time() - start_time) * 1000)
            result.execution_time_ms = execution_time
            
            return result
            
        except Exception as e:
            execution_time = int((time.time() - start_time) * 1000)
            logger.error(f"Error executing command {request.command}: {str(e)}")
            
            return ExecutionResult(
                success=False,
                response_data={"error": "Execution failed"},
                execution_time_ms=execution_time,
                status_code=500,
                error_message=str(e)
            )
    
    async def _execute_container(self, command_def: Dict, request, user_context: Dict = None) -> ExecutionResult:
        """Execute local container interaction module"""
        try:
            # Prepare container payload with user context
            payload = {
                "command": request.command,
                "parameters": request.parameters,
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
                },
                "raw_message": request.raw_message,
                "user_context": user_context or {}
            }
            
            session = await self.get_session()
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WaddleBot-Router/1.0',
                'X-WaddleBot-Source': 'router',
                'X-WaddleBot-Type': 'local-interaction'
            }
            
            # Add custom headers from command definition
            if command_def.get('headers'):
                headers.update(command_def['headers'])
            
            method = command_def.get('method', 'POST').upper()
            
            async with session.request(
                method,
                command_def['location_url'],
                json=payload if method in ['POST', 'PUT', 'PATCH'] else None,
                params=payload if method == 'GET' else None,
                headers=headers
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = {"response": await response.text()}
                
                return ExecutionResult(
                    success=200 <= response.status < 300,
                    response_data=response_data,
                    execution_time_ms=0,
                    status_code=response.status
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                response_data={"error": str(e)},
                execution_time_ms=0,
                status_code=500,
                error_message=str(e)
            )
    
    async def _execute_lambda(self, command_def: Dict, request, user_context: Dict = None) -> ExecutionResult:
        """Execute AWS Lambda function"""
        try:
            # Prepare Lambda payload with user context
            payload = {
                "command": request.command,
                "parameters": request.parameters,
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
                },
                "raw_message": request.raw_message,
                "user_context": user_context or {}
            }
            
            # Execute with retries
            for attempt in range(self.max_retries + 1):
                try:
                    session = await self.get_session()
                    
                    headers = {
                        'Content-Type': 'application/json',
                        'User-Agent': 'WaddleBot-Router/1.0'
                    }
                    
                    # Add custom headers from command definition
                    if command_def.get('headers'):
                        headers.update(command_def['headers'])
                    
                    async with session.post(
                        command_def['location_url'],
                        json=payload,
                        headers=headers
                    ) as response:
                        response_data = await response.json()
                        
                        return ExecutionResult(
                            success=response.status == 200,
                            response_data=response_data,
                            execution_time_ms=0,  # Will be set by caller
                            status_code=response.status,
                            retry_count=attempt
                        )
                        
                except asyncio.TimeoutError:
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        return ExecutionResult(
                            success=False,
                            response_data={"error": "Request timeout"},
                            execution_time_ms=0,
                            status_code=408,
                            error_message="Timeout after retries",
                            retry_count=attempt
                        )
                
                except Exception as e:
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    else:
                        raise e
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                response_data={"error": str(e)},
                execution_time_ms=0,
                status_code=500,
                error_message=str(e)
            )
    
    async def _execute_openwhisk(self, command_def: Dict, request, user_context: Dict = None) -> ExecutionResult:
        """Execute OpenWhisk action"""
        try:
            # Prepare OpenWhisk payload
            payload = {
                "command": request.command,
                "parameters": request.parameters,
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
                },
                "raw_message": request.raw_message
            }
            
            session = await self.get_session()
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Basic {self.openwhisk_config.auth_key}',
                'User-Agent': 'WaddleBot-Router/1.0'
            }
            
            # Add custom headers from command definition
            if command_def.get('headers'):
                headers.update(command_def['headers'])
            
            async with session.post(
                command_def['location_url'],
                json=payload,
                headers=headers
            ) as response:
                response_data = await response.json()
                
                return ExecutionResult(
                    success=response.status == 200,
                    response_data=response_data,
                    execution_time_ms=0,
                    status_code=response.status
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                response_data={"error": str(e)},
                execution_time_ms=0,
                status_code=500,
                error_message=str(e)
            )
    
    async def _execute_webhook(self, command_def: Dict, request, user_context: Dict = None) -> ExecutionResult:
        """Execute generic webhook"""
        try:
            # Prepare webhook payload with user context
            payload = {
                "command": request.command,
                "parameters": request.parameters,
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
                },
                "raw_message": request.raw_message,
                "user_context": user_context or {}
            }
            
            session = await self.get_session()
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'WaddleBot-Router/1.0'
            }
            
            # Add custom headers from command definition
            if command_def.get('headers'):
                headers.update(command_def['headers'])
            
            method = command_def.get('method', 'POST').upper()
            
            async with session.request(
                method,
                command_def['location_url'],
                json=payload if method in ['POST', 'PUT', 'PATCH'] else None,
                params=payload if method == 'GET' else None,
                headers=headers
            ) as response:
                try:
                    response_data = await response.json()
                except:
                    response_data = {"response": await response.text()}
                
                return ExecutionResult(
                    success=200 <= response.status < 300,
                    response_data=response_data,
                    execution_time_ms=0,
                    status_code=response.status
                )
                
        except Exception as e:
            return ExecutionResult(
                success=False,
                response_data={"error": str(e)},
                execution_time_ms=0,
                status_code=500,
                error_message=str(e)
            )
    
    async def close(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()