"""
WebSocket Service for Browser Source Module
Handles WebSocket connections and real-time communication
"""

import logging
import json
import asyncio
import websockets
import threading
import uuid
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class WebSocketService:
    """Service for managing WebSocket connections"""
    
    def __init__(self, config, browser_service):
        self.config = config
        self.browser_service = browser_service
        self.server = None
        self.running = False
        
        # Connection tracking
        self.active_connections = {}  # {connection_id: connection_info}
        
    async def handle_connection(self, websocket, path):
        """Handle a new WebSocket connection"""
        connection_id = str(uuid.uuid4())
        
        try:
            # Parse path to get community token and source type
            path_parts = path.strip('/').split('/')
            if len(path_parts) < 2:
                await websocket.close(code=1008, reason="Invalid path")
                return
            
            community_token = path_parts[0]
            source_type = path_parts[1]
            
            # Validate token
            token_info = self.browser_service.validate_token(community_token)
            if not token_info:
                await websocket.close(code=1008, reason="Invalid token")
                return
            
            community_id = token_info['community_id']
            expected_source_type = token_info['source_type']
            
            # Verify source type matches
            if source_type != expected_source_type:
                await websocket.close(code=1008, reason="Source type mismatch")
                return
            
            # Store connection info
            self.active_connections[connection_id] = {
                'websocket': websocket,
                'community_id': community_id,
                'source_type': source_type,
                'connected_at': datetime.utcnow(),
                'last_ping': datetime.utcnow()
            }
            
            # Register with browser service
            self.browser_service.add_connection(connection_id, community_id, source_type, websocket)
            
            logger.info(f"WebSocket connected: {connection_id} for {community_id}/{source_type}")
            
            # Send initial connection message
            await websocket.send(json.dumps({
                'type': 'connected',
                'connection_id': connection_id,
                'community_id': community_id,
                'source_type': source_type,
                'timestamp': datetime.utcnow().isoformat()
            }))
            
            # Handle incoming messages
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(connection_id, data)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON from {connection_id}: {message}")
                except Exception as e:
                    logger.error(f"Message handling error for {connection_id}: {str(e)}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed: {connection_id}")
        except Exception as e:
            logger.error(f"WebSocket connection error: {str(e)}")
        finally:
            # Clean up connection
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            
            # Remove from browser service
            self.browser_service._remove_connection(connection_id)
    
    async def _handle_message(self, connection_id: str, data: Dict):
        """Handle incoming WebSocket message"""
        try:
            message_type = data.get('type')
            
            if message_type == 'ping':
                # Update last ping time
                if connection_id in self.active_connections:
                    self.active_connections[connection_id]['last_ping'] = datetime.utcnow()
                
                # Send pong response
                websocket = self.active_connections[connection_id]['websocket']
                await websocket.send(json.dumps({
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                }))
                
            elif message_type == 'status':
                # Send connection status
                connection_info = self.active_connections[connection_id]
                websocket = connection_info['websocket']
                
                await websocket.send(json.dumps({
                    'type': 'status',
                    'connection_id': connection_id,
                    'community_id': connection_info['community_id'],
                    'source_type': connection_info['source_type'],
                    'connected_at': connection_info['connected_at'].isoformat(),
                    'uptime': (datetime.utcnow() - connection_info['connected_at']).total_seconds()
                }))
                
            elif message_type == 'analytics':
                # Handle analytics data
                connection_info = self.active_connections[connection_id]
                community_id = connection_info['community_id']
                source_type = connection_info['source_type']
                
                # Store analytics in database
                self.browser_service.db.browser_source_analytics.insert(
                    community_id=community_id,
                    source_type=source_type,
                    event_type=data.get('event_type', 'unknown'),
                    event_data=json.dumps(data.get('event_data', {})),
                    created_at=datetime.utcnow()
                )
                self.browser_service.db.commit()
                
            elif message_type == 'error':
                # Log client-side errors
                connection_info = self.active_connections[connection_id]
                logger.error(f"Client error from {connection_info['community_id']}/{connection_info['source_type']}: {data.get('error', 'Unknown error')}")
                
            else:
                logger.warning(f"Unknown message type from {connection_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Message handling error: {str(e)}")
    
    def start(self):
        """Start the WebSocket server"""
        if self.running:
            return
        
        def run_server():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Create WebSocket server
                server = websockets.serve(
                    self._websocket_handler,
                    self.config.WEBSOCKET_HOST,
                    self.config.WEBSOCKET_PORT,
                    max_size=10**6,  # 1MB max message size
                    max_queue=100,   # Max queue size
                    ping_interval=30, # Ping every 30 seconds
                    ping_timeout=10   # Ping timeout
                )
                
                self.server = loop.run_until_complete(server)
                self.running = True
                
                logger.info(f"WebSocket server started on {self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}")
                
                # Run forever
                loop.run_forever()
                
            except Exception as e:
                logger.error(f"WebSocket server error: {str(e)}")
                self.running = False
        
        # Start server in background thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
    
    async def _websocket_handler(self, websocket, path):
        """WebSocket handler wrapper"""
        await self.handle_connection(websocket, path)
    
    def stop(self):
        """Stop the WebSocket server"""
        if self.server and self.running:
            self.server.close()
            self.running = False
            logger.info("WebSocket server stopped")
    
    def get_stats(self) -> Dict:
        """Get WebSocket connection statistics"""
        try:
            stats = {
                'total_connections': len(self.active_connections),
                'connections_by_type': {},
                'connections_by_community': {}
            }
            
            # Count by source type
            for connection_info in self.active_connections.values():
                source_type = connection_info['source_type']
                community_id = connection_info['community_id']
                
                if source_type not in stats['connections_by_type']:
                    stats['connections_by_type'][source_type] = 0
                stats['connections_by_type'][source_type] += 1
                
                if community_id not in stats['connections_by_community']:
                    stats['connections_by_community'][community_id] = 0
                stats['connections_by_community'][community_id] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get WebSocket stats: {str(e)}")
            return {}
    
    async def broadcast_message(self, message: Dict, community_id: str = None, source_type: str = None):
        """Broadcast message to connections"""
        try:
            message_json = json.dumps(message)
            
            # Send to all matching connections
            for connection_id, connection_info in self.active_connections.items():
                try:
                    # Filter by community and source type if specified
                    if community_id and connection_info['community_id'] != community_id:
                        continue
                    
                    if source_type and connection_info['source_type'] != source_type:
                        continue
                    
                    # Send message
                    websocket = connection_info['websocket']
                    await websocket.send(message_json)
                    
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {connection_id}: {str(e)}")
                    # Connection might be dead, will be cleaned up later
                    
        except Exception as e:
            logger.error(f"Broadcast failed: {str(e)}")
    
    def cleanup_stale_connections(self):
        """Clean up stale connections"""
        try:
            current_time = datetime.utcnow()
            stale_connections = []
            
            for connection_id, connection_info in self.active_connections.items():
                # Check if connection is stale (no ping in 5 minutes)
                if (current_time - connection_info['last_ping']).total_seconds() > 300:
                    stale_connections.append(connection_id)
            
            # Remove stale connections
            for connection_id in stale_connections:
                try:
                    if connection_id in self.active_connections:
                        websocket = self.active_connections[connection_id]['websocket']
                        asyncio.create_task(websocket.close(code=1001, reason="Stale connection"))
                        del self.active_connections[connection_id]
                        
                        logger.info(f"Cleaned up stale connection: {connection_id}")
                        
                except Exception as e:
                    logger.error(f"Error cleaning up connection {connection_id}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Connection cleanup failed: {str(e)}")
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict]:
        """Get information about a specific connection"""
        return self.active_connections.get(connection_id)