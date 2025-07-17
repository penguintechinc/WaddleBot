"""
Browser Source Service
Manages browser source displays, queues, and WebSocket communication
"""

import logging
import json
import secrets
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor
import queue
import threading

logger = logging.getLogger(__name__)

class BrowserSourceService:
    """Service for managing browser source displays and queues"""
    
    def __init__(self, config, db, executor: ThreadPoolExecutor):
        self.config = config
        self.db = db
        self.executor = executor
        
        # In-memory queues for real-time processing
        self.ticker_queues = {}  # {community_id: queue.Queue}
        self.media_queues = {}   # {community_id: queue.Queue}
        self.general_queues = {} # {community_id: queue.Queue}
        
        # WebSocket connections
        self.connections = {}  # {connection_id: websocket}
        self.community_connections = {}  # {community_id: {source_type: [connection_ids]}}
        
        # Thread locks for thread safety
        self.queue_lock = threading.Lock()
        self.connection_lock = threading.Lock()
        
        # Background processing flags
        self.processing_active = True
        
    def generate_community_token(self, community_id: str, source_type: str) -> str:
        """Generate or retrieve token for community browser source"""
        try:
            # Check if token already exists
            existing = self.db(
                (self.db.browser_source_tokens.community_id == community_id) &
                (self.db.browser_source_tokens.source_type == source_type) &
                (self.db.browser_source_tokens.is_active == True)
            ).select().first()
            
            if existing:
                return existing.token
            
            # Generate new token
            token = secrets.token_urlsafe(self.config.TOKEN_LENGTH)
            
            # Store in database
            self.db.browser_source_tokens.insert(
                community_id=community_id,
                source_type=source_type,
                token=token,
                is_active=True,
                created_at=datetime.utcnow()
            )
            self.db.commit()
            
            logger.info(f"Generated token for community {community_id} source {source_type}")
            return token
            
        except Exception as e:
            logger.error(f"Failed to generate token: {str(e)}")
            return None
    
    def validate_token(self, token: str) -> Optional[Dict]:
        """Validate token and return community info"""
        try:
            token_record = self.db(
                (self.db.browser_source_tokens.token == token) &
                (self.db.browser_source_tokens.is_active == True)
            ).select().first()
            
            if token_record:
                return {
                    'community_id': token_record.community_id,
                    'source_type': token_record.source_type,
                    'created_at': token_record.created_at
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Token validation failed: {str(e)}")
            return None
    
    def queue_ticker_message(self, community_id: str, message_data: Dict):
        """Queue a ticker message for display"""
        try:
            # Add to in-memory queue
            with self.queue_lock:
                if community_id not in self.ticker_queues:
                    self.ticker_queues[community_id] = queue.Queue(maxsize=self.config.TICKER_QUEUE_SIZE)
                
                if not self.ticker_queues[community_id].full():
                    self.ticker_queues[community_id].put(message_data)
                    logger.info(f"Queued ticker message for community {community_id}")
                else:
                    logger.warning(f"Ticker queue full for community {community_id}")
            
            # Also store in database for persistence
            self.db.ticker_message_queue.insert(
                community_id=community_id,
                message=message_data.get('text', ''),
                priority=message_data.get('priority', 5),
                duration=message_data.get('duration', self.config.DEFAULT_TICKER_DURATION),
                style=message_data.get('style', 'default'),
                created_at=datetime.utcnow()
            )
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to queue ticker message: {str(e)}")
    
    def send_media_update(self, community_id: str, media_data: Dict):
        """Send media update to connected browser sources"""
        try:
            # Send to WebSocket connections immediately
            self._broadcast_to_community(community_id, 'media', media_data)
            
            # Store in database
            self.db.media_display_queue.insert(
                community_id=community_id,
                media_type=media_data.get('media_type', 'unknown'),
                media_url=media_data.get('media_url', ''),
                media_data=json.dumps(media_data.get('media_data', {})),
                duration=media_data.get('duration', self.config.DEFAULT_MEDIA_DURATION),
                created_at=datetime.utcnow()
            )
            self.db.commit()
            
            logger.info(f"Sent media update to community {community_id}")
            
        except Exception as e:
            logger.error(f"Failed to send media update: {str(e)}")
    
    def send_general_update(self, community_id: str, content_data: Dict):
        """Send general content update to connected browser sources"""
        try:
            # Send to WebSocket connections immediately
            self._broadcast_to_community(community_id, 'general', content_data)
            
            # Store in database
            self.db.general_content_queue.insert(
                community_id=community_id,
                content_type=content_data.get('content_type', 'html'),
                content=content_data.get('content', ''),
                style=json.dumps(content_data.get('style', {})),
                duration=content_data.get('duration', 0),
                created_at=datetime.utcnow()
            )
            self.db.commit()
            
            logger.info(f"Sent general update to community {community_id}")
            
        except Exception as e:
            logger.error(f"Failed to send general update: {str(e)}")
    
    def _broadcast_to_community(self, community_id: str, source_type: str, data: Dict):
        """Broadcast data to all connected browser sources for a community"""
        try:
            with self.connection_lock:
                if community_id in self.community_connections:
                    if source_type in self.community_connections[community_id]:
                        connection_ids = self.community_connections[community_id][source_type].copy()
                        
                        for connection_id in connection_ids:
                            if connection_id in self.connections:
                                try:
                                    # Send data via WebSocket
                                    websocket = self.connections[connection_id]
                                    asyncio.create_task(websocket.send(json.dumps(data)))
                                except Exception as e:
                                    logger.error(f"Failed to send to connection {connection_id}: {str(e)}")
                                    # Remove dead connection
                                    self._remove_connection(connection_id)
                        
        except Exception as e:
            logger.error(f"Broadcast failed: {str(e)}")
    
    def add_connection(self, connection_id: str, community_id: str, source_type: str, websocket):
        """Add a new WebSocket connection"""
        try:
            with self.connection_lock:
                self.connections[connection_id] = websocket
                
                if community_id not in self.community_connections:
                    self.community_connections[community_id] = {}
                
                if source_type not in self.community_connections[community_id]:
                    self.community_connections[community_id][source_type] = []
                
                self.community_connections[community_id][source_type].append(connection_id)
            
            # Store in database
            self.db.browser_source_connections.insert(
                community_id=community_id,
                source_type=source_type,
                connection_id=connection_id,
                connected_at=datetime.utcnow(),
                is_active=True
            )
            self.db.commit()
            
            logger.info(f"Added connection {connection_id} for {community_id}/{source_type}")
            
        except Exception as e:
            logger.error(f"Failed to add connection: {str(e)}")
    
    def _remove_connection(self, connection_id: str):
        """Remove a WebSocket connection"""
        try:
            with self.connection_lock:
                if connection_id in self.connections:
                    del self.connections[connection_id]
                
                # Remove from community connections
                for community_id in self.community_connections:
                    for source_type in self.community_connections[community_id]:
                        if connection_id in self.community_connections[community_id][source_type]:
                            self.community_connections[community_id][source_type].remove(connection_id)
            
            # Update database
            self.db(
                self.db.browser_source_connections.connection_id == connection_id
            ).update(is_active=False)
            self.db.commit()
            
            logger.info(f"Removed connection {connection_id}")
            
        except Exception as e:
            logger.error(f"Failed to remove connection: {str(e)}")
    
    def process_ticker_queues(self):
        """Process ticker message queues"""
        try:
            with self.queue_lock:
                for community_id in list(self.ticker_queues.keys()):
                    try:
                        message_data = self.ticker_queues[community_id].get_nowait()
                        
                        # Send to WebSocket connections
                        self._broadcast_to_community(community_id, 'ticker', message_data)
                        
                        # Mark as processed in database
                        self.db(
                            (self.db.ticker_message_queue.community_id == community_id) &
                            (self.db.ticker_message_queue.message == message_data.get('text', '')) &
                            (self.db.ticker_message_queue.is_processed == False)
                        ).update(
                            processed_at=datetime.utcnow(),
                            is_processed=True
                        )
                        
                    except queue.Empty:
                        continue
                    except Exception as e:
                        logger.error(f"Failed to process ticker queue for {community_id}: {str(e)}")
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Ticker queue processing failed: {str(e)}")
    
    def cleanup_old_data(self):
        """Clean up old data from database"""
        try:
            # Clean up old history (keep last 30 days)
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            self.db(
                self.db.browser_source_history.created_at < cutoff_date
            ).delete()
            
            self.db(
                self.db.browser_source_access_log.accessed_at < cutoff_date
            ).delete()
            
            # Clean up processed queue items older than 1 hour
            queue_cutoff = datetime.utcnow() - timedelta(hours=1)
            
            self.db(
                (self.db.ticker_message_queue.is_processed == True) &
                (self.db.ticker_message_queue.processed_at < queue_cutoff)
            ).delete()
            
            self.db(
                (self.db.media_display_queue.is_processed == True) &
                (self.db.media_display_queue.processed_at < queue_cutoff)
            ).delete()
            
            self.db(
                (self.db.general_content_queue.is_processed == True) &
                (self.db.general_content_queue.processed_at < queue_cutoff)
            ).delete()
            
            # Clean up inactive connections
            self.db(
                (self.db.browser_source_connections.is_active == False) &
                (self.db.browser_source_connections.connected_at < cutoff_date)
            ).delete()
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {str(e)}")
    
    def get_queue_stats(self) -> Dict:
        """Get queue statistics"""
        try:
            stats = {
                'ticker_queues': {},
                'total_connections': len(self.connections),
                'community_connections': {}
            }
            
            # Queue sizes
            with self.queue_lock:
                for community_id, q in self.ticker_queues.items():
                    stats['ticker_queues'][community_id] = q.qsize()
            
            # Connection stats
            with self.connection_lock:
                for community_id in self.community_connections:
                    stats['community_connections'][community_id] = {}
                    for source_type in self.community_connections[community_id]:
                        stats['community_connections'][community_id][source_type] = len(
                            self.community_connections[community_id][source_type]
                        )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {str(e)}")
            return {}
    
    def get_community_urls(self, community_id: str) -> Dict:
        """Get browser source URLs for a community"""
        try:
            urls = {}
            
            for source_type in ['ticker', 'media', 'general']:
                token = self.generate_community_token(community_id, source_type)
                if token:
                    urls[source_type] = {
                        'url': f"{self.config.BASE_URL}/browser/source/{token}/{source_type}",
                        'token': token
                    }
            
            return urls
            
        except Exception as e:
            logger.error(f"Failed to get community URLs: {str(e)}")
            return {}
    
    def shutdown(self):
        """Shutdown the service"""
        self.processing_active = False
        
        # Close all WebSocket connections
        with self.connection_lock:
            for connection_id in list(self.connections.keys()):
                try:
                    self.connections[connection_id].close()
                except:
                    pass
            
            self.connections.clear()
            self.community_connections.clear()
        
        logger.info("Browser source service shutdown complete")