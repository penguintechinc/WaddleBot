"""
Memories Interaction Module for WaddleBot

Handles quotes, reminders, and cool URLs for each community.
Community managers, moderators, and users with 'memories' label can manage content.
"""

from py4web import DAL, Field, action, request, redirect, HTTP
from py4web.utils.auth import Auth
from py4web.utils.cors import CORS
from py4web.core import Fixture
import os
import json
import logging
import requests
import re
import urllib.parse
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, List, Optional, Any
import asyncio
import time

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DB_URI = os.environ.get("DATABASE_URL", "sqlite://memories.db")
if DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

db = DAL(DB_URI, pool_size=10, migrate=True)

# Enable CORS
CORS(origins=["*"])

# Configuration
CORE_API_URL = os.environ.get("CORE_API_URL", "http://router:8000")
ROUTER_API_URL = os.environ.get("ROUTER_API_URL", "http://router:8000/router")
LABELS_API_URL = os.environ.get("LABELS_API_URL", "http://labels-core:8025")
MODULE_NAME = os.environ.get("MODULE_NAME", "memories_interaction_module")
MODULE_VERSION = os.environ.get("MODULE_VERSION", "1.0.0")
MODULE_PORT = int(os.environ.get("MODULE_PORT", "8031"))

# Database Models
db.define_table(
    'memories',
    Field('id', 'id'),
    Field('community_id', 'integer', required=True),
    Field('entity_id', 'string', required=True),
    Field('memory_type', 'string', required=True),  # quote, reminder, url
    Field('title', 'string', required=True),
    Field('content', 'text', required=True),
    Field('url', 'string'),  # For URL type memories
    Field('author', 'string'),  # For quotes
    Field('context', 'text'),  # Additional context
    Field('tags', 'json', default=[]),
    Field('created_by', 'string', required=True),
    Field('created_by_name', 'string'),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    Field('is_active', 'boolean', default=True),
    Field('usage_count', 'integer', default=0),
    Field('last_used', 'datetime'),
    migrate=True
)

db.define_table(
    'reminders',
    Field('id', 'id'),
    Field('memory_id', 'reference memories'),
    Field('community_id', 'integer', required=True),
    Field('entity_id', 'string', required=True),
    Field('user_id', 'string', required=True),
    Field('user_name', 'string'),
    Field('reminder_text', 'text', required=True),
    Field('remind_at', 'datetime', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('is_sent', 'boolean', default=False),
    Field('sent_at', 'datetime'),
    Field('is_recurring', 'boolean', default=False),
    Field('recurring_pattern', 'string'),  # daily, weekly, monthly
    Field('recurring_end', 'datetime'),
    migrate=True
)

db.define_table(
    'memory_reactions',
    Field('id', 'id'),
    Field('memory_id', 'reference memories', required=True),
    Field('user_id', 'string', required=True),
    Field('reaction_type', 'string', required=True),  # like, love, laugh, helpful
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

db.define_table(
    'memory_categories',
    Field('id', 'id'),
    Field('community_id', 'integer', required=True),
    Field('name', 'string', required=True),
    Field('description', 'text'),
    Field('color', 'string', default='#007bff'),
    Field('icon', 'string', default='📝'),
    Field('created_by', 'string', required=True),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Create indexes
try:
    db.executesql('CREATE INDEX IF NOT EXISTS idx_memories_community_type ON memories(community_id, memory_type);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_memories_active ON memories(is_active);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_memories_created_by ON memories(created_by);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_memories_tags ON memories USING gin(tags);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reminders_remind_at ON reminders(remind_at, is_sent);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_memory_reactions_memory ON memory_reactions(memory_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_memory_categories_community ON memory_categories(community_id);')
except:
    pass

db.commit()

# Thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=20)

class MemoriesService:
    """Service for managing memories"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.reminder_thread = None
        self.reminder_running = False
        self.start_reminder_processor()
    
    def start_reminder_processor(self):
        """Start the reminder processing thread"""
        if not self.reminder_running:
            self.reminder_running = True
            self.reminder_thread = threading.Thread(target=self.process_reminders, daemon=True)
            self.reminder_thread.start()
            logger.info("Reminder processor started")
    
    def process_reminders(self):
        """Process pending reminders"""
        while self.reminder_running:
            try:
                now = datetime.utcnow()
                
                # Get pending reminders
                pending_reminders = db(
                    (db.reminders.remind_at <= now) &
                    (db.reminders.is_sent == False)
                ).select()
                
                for reminder in pending_reminders:
                    try:
                        # Send reminder
                        self.send_reminder(reminder)
                        
                        # Mark as sent
                        db(db.reminders.id == reminder.id).update(
                            is_sent=True,
                            sent_at=now
                        )
                        
                        # Create recurring reminder if needed
                        if reminder.is_recurring:
                            self.create_recurring_reminder(reminder)
                        
                        db.commit()
                        logger.info(f"Reminder sent to {reminder.user_name}")
                        
                    except Exception as e:
                        logger.error(f"Error sending reminder {reminder.id}: {str(e)}")
                
                # Sleep for 60 seconds before next check
                time.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in reminder processor: {str(e)}")
                time.sleep(60)
    
    def send_reminder(self, reminder):
        """Send a reminder to the user"""
        try:
            # Format reminder message
            message = f"⏰ Reminder: {reminder.reminder_text}"
            
            # Send via router
            response_data = {
                'session_id': f"reminder_{reminder.id}_{int(time.time())}",
                'success': True,
                'response_action': 'chat',
                'chat_message': message
            }
            
            # Post to router responses endpoint
            router_responses_url = f"{ROUTER_API_URL}/responses"
            requests.post(router_responses_url, json=response_data, timeout=5)
            
        except Exception as e:
            logger.error(f"Error sending reminder notification: {str(e)}")
    
    def create_recurring_reminder(self, base_reminder):
        """Create next recurring reminder"""
        try:
            if not base_reminder.is_recurring or not base_reminder.recurring_pattern:
                return
            
            next_time = base_reminder.remind_at
            
            if base_reminder.recurring_pattern == 'daily':
                next_time += timedelta(days=1)
            elif base_reminder.recurring_pattern == 'weekly':
                next_time += timedelta(weeks=1)
            elif base_reminder.recurring_pattern == 'monthly':
                next_time += timedelta(days=30)  # Approximate
            
            # Check if we should create the next reminder
            if base_reminder.recurring_end and next_time > base_reminder.recurring_end:
                return
            
            # Create next reminder
            db.reminders.insert(
                memory_id=base_reminder.memory_id,
                community_id=base_reminder.community_id,
                entity_id=base_reminder.entity_id,
                user_id=base_reminder.user_id,
                user_name=base_reminder.user_name,
                reminder_text=base_reminder.reminder_text,
                remind_at=next_time,
                is_recurring=True,
                recurring_pattern=base_reminder.recurring_pattern,
                recurring_end=base_reminder.recurring_end
            )
            
        except Exception as e:
            logger.error(f"Error creating recurring reminder: {str(e)}")
    
    def check_permissions(self, user_id: str, community_id: int) -> bool:
        """Check if user has permissions to manage memories"""
        try:
            # Check for memories label
            response = requests.get(
                f"{LABELS_API_URL}/api/v1/users/{user_id}/labels",
                params={'community_id': community_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                labels = data.get('labels', [])
                if 'memories' in labels:
                    return True
            
            # Check for community roles (manager, moderator)
            # This would typically integrate with RBAC service
            # For now, return True for testing
            return True
            
        except Exception as e:
            logger.error(f"Error checking permissions: {str(e)}")
            return False
    
    def add_memory(self, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new memory"""
        try:
            # Validate URL if it's a URL memory
            if memory_data['memory_type'] == 'url':
                if not self.validate_url(memory_data.get('url', '')):
                    return {'success': False, 'error': 'Invalid URL provided'}
            
            with self.lock:
                memory_id = db.memories.insert(
                    community_id=memory_data['community_id'],
                    entity_id=memory_data['entity_id'],
                    memory_type=memory_data['memory_type'],
                    title=memory_data['title'],
                    content=memory_data['content'],
                    url=memory_data.get('url'),
                    author=memory_data.get('author'),
                    context=memory_data.get('context'),
                    tags=memory_data.get('tags', []),
                    created_by=memory_data['created_by'],
                    created_by_name=memory_data.get('created_by_name', memory_data['created_by'])
                )
                
                db.commit()
                
                return {
                    'success': True,
                    'memory_id': memory_id,
                    'type': memory_data['memory_type']
                }
                
        except Exception as e:
            logger.error(f"Error adding memory: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_memories(self, community_id: int, memory_type: str = None, search: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get memories for a community"""
        try:
            query = (db.memories.community_id == community_id) & (db.memories.is_active == True)
            
            if memory_type:
                query &= (db.memories.memory_type == memory_type)
            
            if search:
                search_query = (
                    (db.memories.title.contains(search)) |
                    (db.memories.content.contains(search)) |
                    (db.memories.author.contains(search))
                )
                query &= search_query
            
            memories = db(query).select(
                orderby=~db.memories.created_at,
                limitby=(0, limit)
            )
            
            result = []
            for memory in memories:
                # Get reaction counts
                reactions = db(db.memory_reactions.memory_id == memory.id).select()
                reaction_counts = {}
                for reaction in reactions:
                    reaction_counts[reaction.reaction_type] = reaction_counts.get(reaction.reaction_type, 0) + 1
                
                result.append({
                    'id': memory.id,
                    'memory_type': memory.memory_type,
                    'title': memory.title,
                    'content': memory.content,
                    'url': memory.url,
                    'author': memory.author,
                    'context': memory.context,
                    'tags': memory.tags or [],
                    'created_by': memory.created_by,
                    'created_by_name': memory.created_by_name,
                    'created_at': memory.created_at.isoformat() if memory.created_at else None,
                    'usage_count': memory.usage_count,
                    'last_used': memory.last_used.isoformat() if memory.last_used else None,
                    'reactions': reaction_counts
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting memories: {str(e)}")
            return []
    
    def update_memory(self, memory_id: int, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a memory"""
        try:
            with self.lock:
                memory = db.memories[memory_id]
                if not memory:
                    return {'success': False, 'error': 'Memory not found'}
                
                # Check permissions
                if not self.check_permissions(user_id, memory.community_id):
                    return {'success': False, 'error': 'Permission denied'}
                
                # Update memory
                update_data = {}
                allowed_fields = ['title', 'content', 'url', 'author', 'context', 'tags']
                
                for field in allowed_fields:
                    if field in updates:
                        update_data[field] = updates[field]
                
                if update_data:
                    db(db.memories.id == memory_id).update(**update_data)
                    db.commit()
                
                return {'success': True, 'memory_id': memory_id}
                
        except Exception as e:
            logger.error(f"Error updating memory: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def delete_memory(self, memory_id: int, user_id: str) -> Dict[str, Any]:
        """Delete a memory"""
        try:
            with self.lock:
                memory = db.memories[memory_id]
                if not memory:
                    return {'success': False, 'error': 'Memory not found'}
                
                # Check permissions
                if not self.check_permissions(user_id, memory.community_id):
                    return {'success': False, 'error': 'Permission denied'}
                
                # Soft delete
                db(db.memories.id == memory_id).update(is_active=False)
                db.commit()
                
                return {'success': True, 'memory_id': memory_id}
                
        except Exception as e:
            logger.error(f"Error deleting memory: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def add_reminder(self, reminder_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a reminder"""
        try:
            with self.lock:
                reminder_id = db.reminders.insert(
                    community_id=reminder_data['community_id'],
                    entity_id=reminder_data['entity_id'],
                    user_id=reminder_data['user_id'],
                    user_name=reminder_data.get('user_name', reminder_data['user_id']),
                    reminder_text=reminder_data['reminder_text'],
                    remind_at=reminder_data['remind_at'],
                    is_recurring=reminder_data.get('is_recurring', False),
                    recurring_pattern=reminder_data.get('recurring_pattern'),
                    recurring_end=reminder_data.get('recurring_end')
                )
                
                db.commit()
                
                return {
                    'success': True,
                    'reminder_id': reminder_id,
                    'remind_at': reminder_data['remind_at'].isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error adding reminder: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def validate_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            if not url:
                return False
            
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            # Parse URL
            parsed = urllib.parse.urlparse(url)
            
            # Check if it has a valid scheme and netloc
            return parsed.scheme in ('http', 'https') and parsed.netloc
            
        except Exception:
            return False
    
    def parse_time_expression(self, time_str: str) -> Optional[datetime]:
        """Parse time expressions like '30 minutes', '2 hours', '1 day'"""
        try:
            time_str = time_str.lower().strip()
            
            # Patterns for parsing
            patterns = [
                (r'(\d+)\s*(?:minute|minutes|min|mins?)', lambda m: timedelta(minutes=int(m.group(1)))),
                (r'(\d+)\s*(?:hour|hours|hr|hrs?)', lambda m: timedelta(hours=int(m.group(1)))),
                (r'(\d+)\s*(?:day|days)', lambda m: timedelta(days=int(m.group(1)))),
                (r'(\d+)\s*(?:week|weeks)', lambda m: timedelta(weeks=int(m.group(1)))),
                (r'(\d+)\s*(?:month|months)', lambda m: timedelta(days=int(m.group(1)) * 30)),
            ]
            
            for pattern, delta_func in patterns:
                match = re.search(pattern, time_str)
                if match:
                    delta = delta_func(match)
                    return datetime.utcnow() + delta
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing time expression: {str(e)}")
            return None
    
    def increment_usage(self, memory_id: int):
        """Increment usage count for a memory"""
        try:
            with self.lock:
                db(db.memories.id == memory_id).update(
                    usage_count=db.memories.usage_count + 1,
                    last_used=datetime.utcnow()
                )
                db.commit()
                
        except Exception as e:
            logger.error(f"Error incrementing usage: {str(e)}")

# Initialize service
memories_service = MemoriesService()

# Health check endpoint
@action('health')
def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        db.executesql('SELECT 1')
        
        return {
            'status': 'healthy',
            'module': MODULE_NAME,
            'version': MODULE_VERSION,
            'timestamp': datetime.utcnow().isoformat(),
            'reminder_processor': memories_service.reminder_running
        }
    except Exception as e:
        response.status = 500
        return {
            'status': 'unhealthy',
            'error': str(e),
            'module': MODULE_NAME,
            'version': MODULE_VERSION
        }

# Main command handler
@action('memories', method=['GET', 'POST'])
def memories_command():
    """Handle memories commands"""
    try:
        data = request.json
        
        if not data:
            raise HTTP(400, "No data provided")
        
        # Extract command parameters
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        user_name = data.get('user_name', user_id)
        community_id = data.get('community_id')
        entity_id = data.get('entity_id')
        command = data.get('command', '').lower()
        parameters = data.get('parameters', [])
        
        if not all([session_id, user_id, community_id, entity_id]):
            raise HTTP(400, "Missing required parameters")
        
        # Route to appropriate handler
        if command == 'add':
            result = handle_add_memory(user_id, user_name, community_id, entity_id, parameters)
        elif command == 'list':
            result = handle_list_memories(community_id, parameters)
        elif command == 'search':
            result = handle_search_memories(community_id, parameters)
        elif command == 'get':
            result = handle_get_memory(community_id, parameters)
        elif command == 'edit':
            result = handle_edit_memory(user_id, parameters)
        elif command == 'delete':
            result = handle_delete_memory(user_id, parameters)
        elif command == 'remind':
            result = handle_remind_me(user_id, user_name, community_id, entity_id, parameters)
        elif command == 'quotes':
            result = handle_random_quote(community_id)
        elif command == 'urls':
            result = handle_list_urls(community_id)
        else:
            result = handle_help()
        
        # Return response to router
        return {
            'session_id': session_id,
            'success': True,
            'response_action': 'general',
            'content_type': 'html',
            'content': result['content'],
            'duration': result.get('duration', 30),
            'style': result.get('style', {'type': 'memories', 'theme': 'default'})
        }
        
    except Exception as e:
        logger.error(f"Error handling memories command: {str(e)}")
        return {
            'session_id': data.get('session_id', ''),
            'success': False,
            'response_action': 'chat',
            'chat_message': f"Error: {str(e)}"
        }

def handle_add_memory(user_id: str, user_name: str, community_id: int, entity_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle adding a memory"""
    try:
        if len(parameters) < 2:
            return {
                'content': '''
                <div class="memories-error">
                    <h3>Usage:</h3>
                    <p><strong>!memories add quote</strong> "Quote text" [author]</p>
                    <p><strong>!memories add url</strong> "Title" "URL" [description]</p>
                    <p><strong>!memories add note</strong> "Title" "Content" [tags]</p>
                </div>
                '''
            }
        
        # Check permissions
        if not memories_service.check_permissions(user_id, community_id):
            return {
                'content': '''
                <div class="memories-error">
                    <p>❌ You don't have permission to add memories. You need the 'memories' label or be a community manager/moderator.</p>
                </div>
                '''
            }
        
        memory_type = parameters[0].lower()
        
        if memory_type == 'quote':
            return handle_add_quote(user_id, user_name, community_id, entity_id, parameters[1:])
        elif memory_type == 'url':
            return handle_add_url(user_id, user_name, community_id, entity_id, parameters[1:])
        elif memory_type == 'note':
            return handle_add_note(user_id, user_name, community_id, entity_id, parameters[1:])
        else:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Invalid memory type. Use: quote, url, or note</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_add_memory: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error adding memory: {str(e)}</p>
            </div>
            '''
        }

def handle_add_quote(user_id: str, user_name: str, community_id: int, entity_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle adding a quote"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories add quote "Quote text" [author]</p>
                </div>
                '''
            }
        
        quote_text = parameters[0]
        author = parameters[1] if len(parameters) > 1 else "Unknown"
        
        memory_data = {
            'community_id': community_id,
            'entity_id': entity_id,
            'memory_type': 'quote',
            'title': f"Quote by {author}",
            'content': quote_text,
            'author': author,
            'created_by': user_id,
            'created_by_name': user_name
        }
        
        result = memories_service.add_memory(memory_data)
        
        if result['success']:
            return {
                'content': f'''
                <div class="memories-success">
                    <h3>✅ Quote Added!</h3>
                    <div class="quote-display">
                        <blockquote>
                            "{quote_text}"
                        </blockquote>
                        <cite>— {author}</cite>
                    </div>
                    <p><em>Added by {user_name}</em></p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="memories-error">
                    <p>Error adding quote: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_add_quote: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error adding quote: {str(e)}</p>
            </div>
            '''
        }

def handle_add_url(user_id: str, user_name: str, community_id: int, entity_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle adding a URL"""
    try:
        if len(parameters) < 2:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories add url "Title" "URL" [description]</p>
                </div>
                '''
            }
        
        title = parameters[0]
        url = parameters[1]
        description = parameters[2] if len(parameters) > 2 else ""
        
        # Validate URL
        if not memories_service.validate_url(url):
            return {
                'content': '''
                <div class="memories-error">
                    <p>Invalid URL format. Please provide a valid URL.</p>
                </div>
                '''
            }
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        memory_data = {
            'community_id': community_id,
            'entity_id': entity_id,
            'memory_type': 'url',
            'title': title,
            'content': description,
            'url': url,
            'created_by': user_id,
            'created_by_name': user_name
        }
        
        result = memories_service.add_memory(memory_data)
        
        if result['success']:
            return {
                'content': f'''
                <div class="memories-success">
                    <h3>✅ URL Added!</h3>
                    <div class="url-display">
                        <h4>🔗 {title}</h4>
                        <p><a href="{url}" target="_blank">{url}</a></p>
                        {f'<p><em>{description}</em></p>' if description else ''}
                    </div>
                    <p><em>Added by {user_name}</em></p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="memories-error">
                    <p>Error adding URL: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_add_url: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error adding URL: {str(e)}</p>
            </div>
            '''
        }

def handle_add_note(user_id: str, user_name: str, community_id: int, entity_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle adding a note"""
    try:
        if len(parameters) < 2:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories add note "Title" "Content" [tags]</p>
                </div>
                '''
            }
        
        title = parameters[0]
        content = parameters[1]
        tags = parameters[2].split(',') if len(parameters) > 2 else []
        
        memory_data = {
            'community_id': community_id,
            'entity_id': entity_id,
            'memory_type': 'note',
            'title': title,
            'content': content,
            'tags': [tag.strip() for tag in tags],
            'created_by': user_id,
            'created_by_name': user_name
        }
        
        result = memories_service.add_memory(memory_data)
        
        if result['success']:
            return {
                'content': f'''
                <div class="memories-success">
                    <h3>✅ Note Added!</h3>
                    <div class="note-display">
                        <h4>📝 {title}</h4>
                        <p>{content}</p>
                        {f'<div class="tags">Tags: {", ".join(tags)}</div>' if tags else ''}
                    </div>
                    <p><em>Added by {user_name}</em></p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="memories-error">
                    <p>Error adding note: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_add_note: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error adding note: {str(e)}</p>
            </div>
            '''
        }

def handle_list_memories(community_id: int, parameters: List[str]) -> Dict[str, Any]:
    """Handle listing memories"""
    try:
        memory_type = parameters[0] if parameters else None
        
        if memory_type and memory_type not in ['quote', 'url', 'note']:
            memory_type = None
        
        memories = memories_service.get_memories(community_id, memory_type)
        
        if not memories:
            type_text = f"{memory_type}s" if memory_type else "memories"
            return {
                'content': f'''
                <div class="memories-info">
                    <p>No {type_text} found.</p>
                </div>
                '''
            }
        
        # Group by type
        grouped = {}
        for memory in memories:
            mem_type = memory['memory_type']
            if mem_type not in grouped:
                grouped[mem_type] = []
            grouped[mem_type].append(memory)
        
        content_parts = []
        
        for mem_type, mem_list in grouped.items():
            type_icon = {'quote': '💬', 'url': '🔗', 'note': '📝'}.get(mem_type, '📄')
            content_parts.append(f'<h3>{type_icon} {mem_type.title()}s ({len(mem_list)})</h3>')
            
            for memory in mem_list[:10]:  # Limit to 10 per type
                if mem_type == 'quote':
                    content_parts.append(f'''
                    <div class="memory-item">
                        <blockquote>"{memory['content']}"</blockquote>
                        <cite>— {memory['author']}</cite>
                        <small>Added by {memory['created_by_name']}</small>
                    </div>
                    ''')
                elif mem_type == 'url':
                    content_parts.append(f'''
                    <div class="memory-item">
                        <h4>🔗 {memory['title']}</h4>
                        <p><a href="{memory['url']}" target="_blank">{memory['url']}</a></p>
                        {f'<p><em>{memory["content"]}</em></p>' if memory['content'] else ''}
                        <small>Added by {memory['created_by_name']}</small>
                    </div>
                    ''')
                elif mem_type == 'note':
                    content_parts.append(f'''
                    <div class="memory-item">
                        <h4>📝 {memory['title']}</h4>
                        <p>{memory['content']}</p>
                        {f'<div class="tags">Tags: {", ".join(memory["tags"])}</div>' if memory['tags'] else ''}
                        <small>Added by {memory['created_by_name']}</small>
                    </div>
                    ''')
        
        return {
            'content': f'''
            <div class="memories-list">
                <h3>📚 Community Memories</h3>
                {''.join(content_parts)}
            </div>
            '''
        }
        
    except Exception as e:
        logger.error(f"Error in handle_list_memories: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error listing memories: {str(e)}</p>
            </div>
            '''
        }

def handle_search_memories(community_id: int, parameters: List[str]) -> Dict[str, Any]:
    """Handle searching memories"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories search "search term"</p>
                </div>
                '''
            }
        
        search_term = parameters[0]
        memories = memories_service.get_memories(community_id, search=search_term)
        
        if not memories:
            return {
                'content': f'''
                <div class="memories-info">
                    <p>No memories found matching "{search_term}".</p>
                </div>
                '''
            }
        
        content_parts = [f'<h3>🔍 Search Results for "{search_term}"</h3>']
        
        for memory in memories[:20]:  # Limit to 20 results
            mem_type = memory['memory_type']
            type_icon = {'quote': '💬', 'url': '🔗', 'note': '📝'}.get(mem_type, '📄')
            
            content_parts.append(f'''
            <div class="memory-item">
                <h4>{type_icon} {memory['title']}</h4>
                <p>{memory['content'][:200]}{'...' if len(memory['content']) > 200 else ''}</p>
                {f'<p><strong>Author:</strong> {memory["author"]}</p>' if memory['author'] else ''}
                {f'<p><strong>URL:</strong> <a href="{memory["url"]}" target="_blank">{memory["url"]}</a></p>' if memory['url'] else ''}
                <small>Added by {memory['created_by_name']} • {mem_type.title()}</small>
            </div>
            ''')
        
        return {
            'content': f'''
            <div class="memories-search">
                {''.join(content_parts)}
            </div>
            '''
        }
        
    except Exception as e:
        logger.error(f"Error in handle_search_memories: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error searching memories: {str(e)}</p>
            </div>
            '''
        }

def handle_get_memory(community_id: int, parameters: List[str]) -> Dict[str, Any]:
    """Handle getting a specific memory"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories get [memory_id]</p>
                </div>
                '''
            }
        
        memory_id = int(parameters[0])
        memory = db.memories[memory_id]
        
        if not memory or memory.community_id != community_id:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Memory not found.</p>
                </div>
                '''
            }
        
        # Increment usage
        memories_service.increment_usage(memory_id)
        
        mem_type = memory.memory_type
        type_icon = {'quote': '💬', 'url': '🔗', 'note': '📝'}.get(mem_type, '📄')
        
        content = f'''
        <div class="memory-detail">
            <h3>{type_icon} {memory.title}</h3>
            <div class="memory-content">
        '''
        
        if mem_type == 'quote':
            content += f'''
                <blockquote>"{memory.content}"</blockquote>
                <cite>— {memory.author}</cite>
            '''
        elif mem_type == 'url':
            content += f'''
                <p><a href="{memory.url}" target="_blank">{memory.url}</a></p>
                {f'<p><em>{memory.content}</em></p>' if memory.content else ''}
            '''
        elif mem_type == 'note':
            content += f'''
                <p>{memory.content}</p>
                {f'<div class="tags">Tags: {", ".join(memory.tags or [])}</div>' if memory.tags else ''}
            '''
        
        content += f'''
            </div>
            <div class="memory-meta">
                <p><strong>Added by:</strong> {memory.created_by_name}</p>
                <p><strong>Created:</strong> {memory.created_at.strftime('%Y-%m-%d %H:%M') if memory.created_at else 'Unknown'}</p>
                <p><strong>Used:</strong> {memory.usage_count} times</p>
            </div>
        </div>
        '''
        
        return {'content': content}
        
    except Exception as e:
        logger.error(f"Error in handle_get_memory: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error getting memory: {str(e)}</p>
            </div>
            '''
        }

def handle_edit_memory(user_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle editing a memory"""
    try:
        if len(parameters) < 3:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories edit [memory_id] [field] "new_value"</p>
                    <p>Fields: title, content, author, url, tags</p>
                </div>
                '''
            }
        
        memory_id = int(parameters[0])
        field = parameters[1].lower()
        new_value = parameters[2]
        
        if field not in ['title', 'content', 'author', 'url', 'tags']:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Invalid field. Use: title, content, author, url, or tags</p>
                </div>
                '''
            }
        
        updates = {}
        if field == 'tags':
            updates[field] = [tag.strip() for tag in new_value.split(',')]
        else:
            updates[field] = new_value
        
        result = memories_service.update_memory(memory_id, user_id, updates)
        
        if result['success']:
            return {
                'content': f'''
                <div class="memories-success">
                    <p>✅ Memory updated successfully!</p>
                    <p><strong>{field.title()}:</strong> {new_value}</p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="memories-error">
                    <p>Error updating memory: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_edit_memory: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error editing memory: {str(e)}</p>
            </div>
            '''
        }

def handle_delete_memory(user_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle deleting a memory"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories delete [memory_id]</p>
                </div>
                '''
            }
        
        memory_id = int(parameters[0])
        result = memories_service.delete_memory(memory_id, user_id)
        
        if result['success']:
            return {
                'content': '''
                <div class="memories-success">
                    <p>✅ Memory deleted successfully!</p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="memories-error">
                    <p>Error deleting memory: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_delete_memory: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error deleting memory: {str(e)}</p>
            </div>
            '''
        }

def handle_remind_me(user_id: str, user_name: str, community_id: int, entity_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle reminder creation"""
    try:
        if len(parameters) < 3:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Usage: !memories remind "reminder text" in "time"</p>
                    <p>Example: !memories remind "Check the server" in "30 minutes"</p>
                    <p>Time formats: X minutes, X hours, X days, X weeks</p>
                </div>
                '''
            }
        
        reminder_text = parameters[0]
        if parameters[1].lower() != 'in':
            return {
                'content': '''
                <div class="memories-error">
                    <p>Invalid format. Use: !memories remind "text" in "time"</p>
                </div>
                '''
            }
        
        time_str = parameters[2]
        remind_at = memories_service.parse_time_expression(time_str)
        
        if not remind_at:
            return {
                'content': '''
                <div class="memories-error">
                    <p>Invalid time format. Use: X minutes, X hours, X days, X weeks</p>
                </div>
                '''
            }
        
        reminder_data = {
            'community_id': community_id,
            'entity_id': entity_id,
            'user_id': user_id,
            'user_name': user_name,
            'reminder_text': reminder_text,
            'remind_at': remind_at
        }
        
        result = memories_service.add_reminder(reminder_data)
        
        if result['success']:
            return {
                'content': f'''
                <div class="memories-success">
                    <h3>⏰ Reminder Set!</h3>
                    <p><strong>Reminder:</strong> {reminder_text}</p>
                    <p><strong>Time:</strong> {remind_at.strftime('%Y-%m-%d %H:%M UTC')}</p>
                    <p><em>You will be reminded in {time_str}</em></p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="memories-error">
                    <p>Error setting reminder: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_remind_me: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error setting reminder: {str(e)}</p>
            </div>
            '''
        }

def handle_random_quote(community_id: int) -> Dict[str, Any]:
    """Handle random quote request"""
    try:
        quotes = memories_service.get_memories(community_id, 'quote')
        
        if not quotes:
            return {
                'content': '''
                <div class="memories-info">
                    <p>No quotes found. Add some quotes with !memories add quote "text" [author]</p>
                </div>
                '''
            }
        
        import random
        quote = random.choice(quotes)
        
        # Increment usage
        memories_service.increment_usage(quote['id'])
        
        return {
            'content': f'''
            <div class="quote-display">
                <h3>💬 Random Quote</h3>
                <blockquote>"{quote['content']}"</blockquote>
                <cite>— {quote['author']}</cite>
                <small>Added by {quote['created_by_name']}</small>
            </div>
            '''
        }
        
    except Exception as e:
        logger.error(f"Error in handle_random_quote: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error getting random quote: {str(e)}</p>
            </div>
            '''
        }

def handle_list_urls(community_id: int) -> Dict[str, Any]:
    """Handle listing URLs"""
    try:
        urls = memories_service.get_memories(community_id, 'url')
        
        if not urls:
            return {
                'content': '''
                <div class="memories-info">
                    <p>No URLs found. Add some URLs with !memories add url "title" "url" [description]</p>
                </div>
                '''
            }
        
        content_parts = ['<h3>🔗 Community URLs</h3>']
        
        for url in urls[:20]:  # Limit to 20
            content_parts.append(f'''
            <div class="url-item">
                <h4>🔗 {url['title']}</h4>
                <p><a href="{url['url']}" target="_blank">{url['url']}</a></p>
                {f'<p><em>{url["content"]}</em></p>' if url['content'] else ''}
                <small>Added by {url['created_by_name']} • Used {url['usage_count']} times</small>
            </div>
            ''')
        
        return {
            'content': f'''
            <div class="urls-list">
                {''.join(content_parts)}
            </div>
            '''
        }
        
    except Exception as e:
        logger.error(f"Error in handle_list_urls: {str(e)}")
        return {
            'content': f'''
            <div class="memories-error">
                <p>Error listing URLs: {str(e)}</p>
            </div>
            '''
        }

def handle_help() -> Dict[str, Any]:
    """Handle help command"""
    return {
        'content': '''
        <div class="memories-help">
            <h3>📚 Memories Commands</h3>
            <div class="command-list">
                <h4>Adding Memories:</h4>
                <p><strong>!memories add quote</strong> "Quote text" [author] - Add a quote</p>
                <p><strong>!memories add url</strong> "Title" "URL" [description] - Add a URL</p>
                <p><strong>!memories add note</strong> "Title" "Content" [tags] - Add a note</p>
                
                <h4>Viewing Memories:</h4>
                <p><strong>!memories list</strong> [quote|url|note] - List memories</p>
                <p><strong>!memories search</strong> "search term" - Search memories</p>
                <p><strong>!memories get</strong> [memory_id] - Get specific memory</p>
                <p><strong>!memories quotes</strong> - Get random quote</p>
                <p><strong>!memories urls</strong> - List all URLs</p>
                
                <h4>Managing Memories:</h4>
                <p><strong>!memories edit</strong> [memory_id] [field] "new_value" - Edit memory</p>
                <p><strong>!memories delete</strong> [memory_id] - Delete memory</p>
                
                <h4>Reminders:</h4>
                <p><strong>!memories remind</strong> "reminder text" in "time" - Set reminder</p>
                <p>Time formats: X minutes, X hours, X days, X weeks</p>
            </div>
            <div class="memories-info">
                <p><strong>Permissions:</strong> Community managers, moderators, and users with the 'memories' label can manage memories.</p>
            </div>
        </div>
        '''
    }

if __name__ == '__main__':
    # Start the application
    from py4web import run
    run(port=MODULE_PORT, host='0.0.0.0')