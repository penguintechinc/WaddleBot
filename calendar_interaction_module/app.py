"""
Calendar Interaction Module for WaddleBot

Handles event creation, management, and approval workflows.
Users can create events that require approval by community admins or moderators
unless they have the 'event-autoapprove' label.
"""

from py4web import DAL, Field, action, request, redirect, HTTP
from py4web.utils.auth import Auth
from py4web.utils.cors import CORS
from py4web.core import Fixture
import os
import json
import logging
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import threading
from typing import Dict, List, Optional, Any

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DB_URI = os.environ.get("DATABASE_URL", "sqlite://calendar.db")
if DB_URI.startswith("postgres://"):
    DB_URI = DB_URI.replace("postgres://", "postgresql://", 1)

db = DAL(DB_URI, pool_size=10, migrate=True)

# Enable CORS
CORS(origins=["*"])

# Configuration
CORE_API_URL = os.environ.get("CORE_API_URL", "http://router:8000")
ROUTER_API_URL = os.environ.get("ROUTER_API_URL", "http://router:8000/router")
MODULE_NAME = os.environ.get("MODULE_NAME", "calendar_interaction_module")
MODULE_VERSION = os.environ.get("MODULE_VERSION", "1.0.0")
MODULE_PORT = int(os.environ.get("MODULE_PORT", "8030"))

# Database Models
db.define_table(
    'events',
    Field('id', 'id'),
    Field('community_id', 'integer', required=True),
    Field('entity_id', 'string', required=True),
    Field('title', 'string', required=True),
    Field('description', 'text'),
    Field('event_date', 'datetime', required=True),
    Field('end_date', 'datetime'),
    Field('location', 'string'),
    Field('max_attendees', 'integer'),
    Field('created_by', 'string', required=True),
    Field('created_by_name', 'string'),
    Field('status', 'string', default='pending'),  # pending, approved, rejected, cancelled
    Field('approved_by', 'string'),
    Field('approved_by_name', 'string'),
    Field('approved_at', 'datetime'),
    Field('rejection_reason', 'text'),
    Field('attendees', 'json', default=[]),
    Field('tags', 'json', default=[]),
    Field('is_recurring', 'boolean', default=False),
    Field('recurring_pattern', 'string'),  # daily, weekly, monthly, yearly
    Field('recurring_end_date', 'datetime'),
    Field('notification_sent', 'boolean', default=False),
    Field('created_at', 'datetime', default=datetime.utcnow),
    Field('updated_at', 'datetime', update=datetime.utcnow),
    migrate=True
)

db.define_table(
    'event_attendees',
    Field('id', 'id'),
    Field('event_id', 'reference events', required=True),
    Field('user_id', 'string', required=True),
    Field('user_name', 'string'),
    Field('status', 'string', default='attending'),  # attending, maybe, not_attending
    Field('joined_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

db.define_table(
    'event_reminders',
    Field('id', 'id'),
    Field('event_id', 'reference events', required=True),
    Field('reminder_time', 'datetime', required=True),
    Field('reminder_type', 'string', default='chat'),  # chat, general
    Field('message', 'text'),
    Field('sent', 'boolean', default=False),
    Field('created_at', 'datetime', default=datetime.utcnow),
    migrate=True
)

# Create indexes
try:
    db.executesql('CREATE INDEX IF NOT EXISTS idx_events_community_status ON events(community_id, status);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_events_created_by ON events(created_by);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_event_attendees_event ON event_attendees(event_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_event_attendees_user ON event_attendees(user_id);')
    db.executesql('CREATE INDEX IF NOT EXISTS idx_event_reminders_time ON event_reminders(reminder_time, sent);')
except:
    pass

db.commit()

# Thread pool for concurrent operations
executor = ThreadPoolExecutor(max_workers=10)

class CalendarService:
    """Service for managing calendar events"""
    
    def __init__(self):
        self.lock = threading.Lock()
    
    def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new event"""
        try:
            with self.lock:
                # Check if user has auto-approve label
                auto_approve = self.check_auto_approve_permission(
                    event_data['created_by'], 
                    event_data['community_id']
                )
                
                # Set initial status
                status = 'approved' if auto_approve else 'pending'
                
                # Create event
                event_id = db.events.insert(
                    community_id=event_data['community_id'],
                    entity_id=event_data['entity_id'],
                    title=event_data['title'],
                    description=event_data.get('description', ''),
                    event_date=event_data['event_date'],
                    end_date=event_data.get('end_date'),
                    location=event_data.get('location', ''),
                    max_attendees=event_data.get('max_attendees'),
                    created_by=event_data['created_by'],
                    created_by_name=event_data.get('created_by_name', event_data['created_by']),
                    status=status,
                    tags=event_data.get('tags', []),
                    is_recurring=event_data.get('is_recurring', False),
                    recurring_pattern=event_data.get('recurring_pattern'),
                    recurring_end_date=event_data.get('recurring_end_date'),
                    approved_by=event_data['created_by'] if auto_approve else None,
                    approved_by_name=event_data.get('created_by_name') if auto_approve else None,
                    approved_at=datetime.utcnow() if auto_approve else None
                )
                
                db.commit()
                
                # Create recurring events if needed
                if event_data.get('is_recurring') and auto_approve:
                    self.create_recurring_events(event_id)
                
                return {
                    'success': True,
                    'event_id': event_id,
                    'status': status,
                    'auto_approved': auto_approve
                }
                
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def approve_event(self, event_id: int, approved_by: str, approved_by_name: str) -> Dict[str, Any]:
        """Approve a pending event"""
        try:
            with self.lock:
                event = db.events[event_id]
                if not event:
                    return {'success': False, 'error': 'Event not found'}
                
                if event.status != 'pending':
                    return {'success': False, 'error': 'Event is not pending approval'}
                
                # Update event status
                db(db.events.id == event_id).update(
                    status='approved',
                    approved_by=approved_by,
                    approved_by_name=approved_by_name,
                    approved_at=datetime.utcnow()
                )
                
                # Create recurring events if needed
                if event.is_recurring:
                    self.create_recurring_events(event_id)
                
                # Create default reminders
                self.create_default_reminders(event_id)
                
                db.commit()
                
                return {'success': True, 'event_id': event_id}
                
        except Exception as e:
            logger.error(f"Error approving event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def reject_event(self, event_id: int, rejected_by: str, reason: str) -> Dict[str, Any]:
        """Reject a pending event"""
        try:
            with self.lock:
                event = db.events[event_id]
                if not event:
                    return {'success': False, 'error': 'Event not found'}
                
                if event.status != 'pending':
                    return {'success': False, 'error': 'Event is not pending approval'}
                
                # Update event status
                db(db.events.id == event_id).update(
                    status='rejected',
                    approved_by=rejected_by,
                    approved_at=datetime.utcnow(),
                    rejection_reason=reason
                )
                
                db.commit()
                
                return {'success': True, 'event_id': event_id}
                
        except Exception as e:
            logger.error(f"Error rejecting event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def join_event(self, event_id: int, user_id: str, user_name: str) -> Dict[str, Any]:
        """Join an event"""
        try:
            with self.lock:
                event = db.events[event_id]
                if not event:
                    return {'success': False, 'error': 'Event not found'}
                
                if event.status != 'approved':
                    return {'success': False, 'error': 'Event is not approved'}
                
                # Check if already joined
                existing = db(
                    (db.event_attendees.event_id == event_id) &
                    (db.event_attendees.user_id == user_id)
                ).select().first()
                
                if existing:
                    return {'success': False, 'error': 'Already joined this event'}
                
                # Check max attendees
                if event.max_attendees:
                    current_count = db(
                        (db.event_attendees.event_id == event_id) &
                        (db.event_attendees.status == 'attending')
                    ).count()
                    
                    if current_count >= event.max_attendees:
                        return {'success': False, 'error': 'Event is full'}
                
                # Add attendee
                db.event_attendees.insert(
                    event_id=event_id,
                    user_id=user_id,
                    user_name=user_name,
                    status='attending'
                )
                
                db.commit()
                
                return {'success': True, 'event_id': event_id}
                
        except Exception as e:
            logger.error(f"Error joining event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def leave_event(self, event_id: int, user_id: str) -> Dict[str, Any]:
        """Leave an event"""
        try:
            with self.lock:
                # Remove attendee
                db(
                    (db.event_attendees.event_id == event_id) &
                    (db.event_attendees.user_id == user_id)
                ).delete()
                
                db.commit()
                
                return {'success': True, 'event_id': event_id}
                
        except Exception as e:
            logger.error(f"Error leaving event: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def get_events(self, community_id: int, status: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get events for a community"""
        try:
            query = db.events.community_id == community_id
            
            if status:
                query &= (db.events.status == status)
            
            events = db(query).select(
                orderby=db.events.event_date,
                limitby=(0, limit)
            )
            
            result = []
            for event in events:
                # Get attendee count
                attendee_count = db(
                    (db.event_attendees.event_id == event.id) &
                    (db.event_attendees.status == 'attending')
                ).count()
                
                result.append({
                    'id': event.id,
                    'title': event.title,
                    'description': event.description,
                    'event_date': event.event_date.isoformat() if event.event_date else None,
                    'end_date': event.end_date.isoformat() if event.end_date else None,
                    'location': event.location,
                    'max_attendees': event.max_attendees,
                    'attendee_count': attendee_count,
                    'created_by': event.created_by,
                    'created_by_name': event.created_by_name,
                    'status': event.status,
                    'tags': event.tags or [],
                    'is_recurring': event.is_recurring,
                    'created_at': event.created_at.isoformat() if event.created_at else None
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting events: {str(e)}")
            return []
    
    def check_auto_approve_permission(self, user_id: str, community_id: int) -> bool:
        """Check if user has auto-approve permission via labels"""
        try:
            # Call labels core module to check for event-autoapprove label
            labels_api_url = os.environ.get("LABELS_API_URL", "http://labels-core:8025")
            
            response = requests.get(
                f"{labels_api_url}/api/v1/users/{user_id}/labels",
                params={'community_id': community_id},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                labels = data.get('labels', [])
                return 'event-autoapprove' in labels
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking auto-approve permission: {str(e)}")
            return False
    
    def create_recurring_events(self, base_event_id: int):
        """Create recurring events based on pattern"""
        try:
            base_event = db.events[base_event_id]
            if not base_event or not base_event.is_recurring:
                return
            
            pattern = base_event.recurring_pattern
            current_date = base_event.event_date
            end_date = base_event.recurring_end_date or (base_event.event_date + timedelta(days=365))
            
            # Calculate recurring dates
            while current_date < end_date:
                if pattern == 'daily':
                    current_date += timedelta(days=1)
                elif pattern == 'weekly':
                    current_date += timedelta(weeks=1)
                elif pattern == 'monthly':
                    current_date += timedelta(days=30)  # Approximate
                elif pattern == 'yearly':
                    current_date += timedelta(days=365)  # Approximate
                else:
                    break
                
                if current_date >= end_date:
                    break
                
                # Create recurring event
                db.events.insert(
                    community_id=base_event.community_id,
                    entity_id=base_event.entity_id,
                    title=base_event.title,
                    description=base_event.description,
                    event_date=current_date,
                    end_date=base_event.end_date + (current_date - base_event.event_date) if base_event.end_date else None,
                    location=base_event.location,
                    max_attendees=base_event.max_attendees,
                    created_by=base_event.created_by,
                    created_by_name=base_event.created_by_name,
                    status='approved',
                    tags=base_event.tags,
                    is_recurring=False,  # Recurring instances are not recurring themselves
                    approved_by=base_event.approved_by,
                    approved_by_name=base_event.approved_by_name,
                    approved_at=base_event.approved_at
                )
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error creating recurring events: {str(e)}")
    
    def create_default_reminders(self, event_id: int):
        """Create default reminders for an event"""
        try:
            event = db.events[event_id]
            if not event:
                return
            
            # Create reminders at 1 day, 1 hour, and 15 minutes before
            reminder_times = [
                event.event_date - timedelta(days=1),
                event.event_date - timedelta(hours=1),
                event.event_date - timedelta(minutes=15)
            ]
            
            for reminder_time in reminder_times:
                if reminder_time > datetime.utcnow():
                    db.event_reminders.insert(
                        event_id=event_id,
                        reminder_time=reminder_time,
                        reminder_type='chat',
                        message=f"Reminder: '{event.title}' starts in {self.format_time_until(reminder_time, event.event_date)}"
                    )
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error creating default reminders: {str(e)}")
    
    def format_time_until(self, from_time: datetime, to_time: datetime) -> str:
        """Format time difference"""
        diff = to_time - from_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''}"
        elif diff.seconds >= 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''}"
        elif diff.seconds >= 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return "less than a minute"

# Initialize service
calendar_service = CalendarService()

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
            'timestamp': datetime.utcnow().isoformat()
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
@action('calendar', method=['GET', 'POST'])
def calendar_command():
    """Handle calendar commands"""
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
        if command == 'create':
            result = handle_create_event(user_id, user_name, community_id, entity_id, parameters)
        elif command == 'list':
            result = handle_list_events(community_id, parameters)
        elif command == 'join':
            result = handle_join_event(user_id, user_name, parameters)
        elif command == 'leave':
            result = handle_leave_event(user_id, parameters)
        elif command == 'approve':
            result = handle_approve_event(user_id, user_name, parameters)
        elif command == 'reject':
            result = handle_reject_event(user_id, parameters)
        elif command == 'cancel':
            result = handle_cancel_event(user_id, parameters)
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
            'style': result.get('style', {'type': 'calendar', 'theme': 'default'})
        }
        
    except Exception as e:
        logger.error(f"Error handling calendar command: {str(e)}")
        return {
            'session_id': data.get('session_id', ''),
            'success': False,
            'response_action': 'chat',
            'chat_message': f"Error: {str(e)}"
        }

def handle_create_event(user_id: str, user_name: str, community_id: int, entity_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle event creation"""
    try:
        if len(parameters) < 2:
            return {
                'content': '''
                <div class="calendar-error">
                    <h3>Usage:</h3>
                    <p>!calendar create "Event Title" "YYYY-MM-DD HH:MM" [description] [location] [max_attendees]</p>
                    <p>Example: !calendar create "Game Night" "2024-01-15 20:00" "Weekly gaming session" "Discord" 8</p>
                </div>
                '''
            }
        
        title = parameters[0]
        date_str = parameters[1]
        description = parameters[2] if len(parameters) > 2 else ""
        location = parameters[3] if len(parameters) > 3 else ""
        max_attendees = int(parameters[4]) if len(parameters) > 4 and parameters[4].isdigit() else None
        
        # Parse date
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        except ValueError:
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Invalid date format. Use YYYY-MM-DD HH:MM</p>
                    <p>Example: 2024-01-15 20:00</p>
                </div>
                '''
            }
        
        # Check if date is in the future
        if event_date <= datetime.utcnow():
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Event date must be in the future.</p>
                </div>
                '''
            }
        
        # Create event
        event_data = {
            'community_id': community_id,
            'entity_id': entity_id,
            'title': title,
            'description': description,
            'event_date': event_date,
            'location': location,
            'max_attendees': max_attendees,
            'created_by': user_id,
            'created_by_name': user_name
        }
        
        result = calendar_service.create_event(event_data)
        
        if result['success']:
            status_message = "Event created and approved!" if result['auto_approved'] else "Event created and pending approval."
            
            return {
                'content': f'''
                <div class="calendar-success">
                    <h3>✅ {status_message}</h3>
                    <div class="event-details">
                        <p><strong>Title:</strong> {title}</p>
                        <p><strong>Date:</strong> {event_date.strftime('%Y-%m-%d %H:%M')}</p>
                        {f'<p><strong>Location:</strong> {location}</p>' if location else ''}
                        {f'<p><strong>Max Attendees:</strong> {max_attendees}</p>' if max_attendees else ''}
                        {f'<p><strong>Description:</strong> {description}</p>' if description else ''}
                    </div>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="calendar-error">
                    <p>Error creating event: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_create_event: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error creating event: {str(e)}</p>
            </div>
            '''
        }

def handle_list_events(community_id: int, parameters: List[str]) -> Dict[str, Any]:
    """Handle event listing"""
    try:
        status_filter = parameters[0] if parameters else None
        if status_filter not in ['pending', 'approved', 'rejected']:
            status_filter = 'approved'
        
        events = calendar_service.get_events(community_id, status_filter)
        
        if not events:
            return {
                'content': f'''
                <div class="calendar-info">
                    <p>No {status_filter} events found.</p>
                </div>
                '''
            }
        
        events_html = []
        for event in events:
            event_date = datetime.fromisoformat(event['event_date'])
            
            events_html.append(f'''
            <div class="event-card">
                <h4>{event['title']}</h4>
                <p><strong>Date:</strong> {event_date.strftime('%Y-%m-%d %H:%M')}</p>
                {f'<p><strong>Location:</strong> {event["location"]}</p>' if event['location'] else ''}
                <p><strong>Attendees:</strong> {event['attendee_count']}{f'/{event["max_attendees"]}' if event['max_attendees'] else ''}</p>
                <p><strong>Status:</strong> {event['status'].title()}</p>
                <p><strong>Created by:</strong> {event['created_by_name']}</p>
                {f'<p><strong>Description:</strong> {event["description"]}</p>' if event['description'] else ''}
            </div>
            ''')
        
        return {
            'content': f'''
            <div class="calendar-list">
                <h3>📅 {status_filter.title()} Events</h3>
                {''.join(events_html)}
            </div>
            '''
        }
        
    except Exception as e:
        logger.error(f"Error in handle_list_events: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error listing events: {str(e)}</p>
            </div>
            '''
        }

def handle_join_event(user_id: str, user_name: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle joining an event"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Usage: !calendar join [event_id]</p>
                </div>
                '''
            }
        
        event_id = int(parameters[0])
        result = calendar_service.join_event(event_id, user_id, user_name)
        
        if result['success']:
            return {
                'content': '''
                <div class="calendar-success">
                    <p>✅ Successfully joined the event!</p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="calendar-error">
                    <p>Error joining event: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_join_event: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error joining event: {str(e)}</p>
            </div>
            '''
        }

def handle_leave_event(user_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle leaving an event"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Usage: !calendar leave [event_id]</p>
                </div>
                '''
            }
        
        event_id = int(parameters[0])
        result = calendar_service.leave_event(event_id, user_id)
        
        if result['success']:
            return {
                'content': '''
                <div class="calendar-success">
                    <p>✅ Successfully left the event!</p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="calendar-error">
                    <p>Error leaving event: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_leave_event: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error leaving event: {str(e)}</p>
            </div>
            '''
        }

def handle_approve_event(user_id: str, user_name: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle event approval"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Usage: !calendar approve [event_id]</p>
                </div>
                '''
            }
        
        event_id = int(parameters[0])
        result = calendar_service.approve_event(event_id, user_id, user_name)
        
        if result['success']:
            return {
                'content': '''
                <div class="calendar-success">
                    <p>✅ Event approved successfully!</p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="calendar-error">
                    <p>Error approving event: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_approve_event: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error approving event: {str(e)}</p>
            </div>
            '''
        }

def handle_reject_event(user_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle event rejection"""
    try:
        if len(parameters) < 2:
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Usage: !calendar reject [event_id] "reason"</p>
                </div>
                '''
            }
        
        event_id = int(parameters[0])
        reason = parameters[1]
        result = calendar_service.reject_event(event_id, user_id, reason)
        
        if result['success']:
            return {
                'content': '''
                <div class="calendar-success">
                    <p>✅ Event rejected successfully!</p>
                </div>
                '''
            }
        else:
            return {
                'content': f'''
                <div class="calendar-error">
                    <p>Error rejecting event: {result['error']}</p>
                </div>
                '''
            }
            
    except Exception as e:
        logger.error(f"Error in handle_reject_event: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error rejecting event: {str(e)}</p>
            </div>
            '''
        }

def handle_cancel_event(user_id: str, parameters: List[str]) -> Dict[str, Any]:
    """Handle event cancellation"""
    try:
        if not parameters:
            return {
                'content': '''
                <div class="calendar-error">
                    <p>Usage: !calendar cancel [event_id]</p>
                </div>
                '''
            }
        
        event_id = int(parameters[0])
        
        # Only creator can cancel
        with calendar_service.lock:
            event = db.events[event_id]
            if not event:
                return {
                    'content': '''
                    <div class="calendar-error">
                        <p>Event not found.</p>
                    </div>
                    '''
                }
            
            if event.created_by != user_id:
                return {
                    'content': '''
                    <div class="calendar-error">
                        <p>Only the event creator can cancel the event.</p>
                    </div>
                    '''
                }
            
            db(db.events.id == event_id).update(status='cancelled')
            db.commit()
        
        return {
            'content': '''
            <div class="calendar-success">
                <p>✅ Event cancelled successfully!</p>
            </div>
            '''
        }
        
    except Exception as e:
        logger.error(f"Error in handle_cancel_event: {str(e)}")
        return {
            'content': f'''
            <div class="calendar-error">
                <p>Error cancelling event: {str(e)}</p>
            </div>
            '''
        }

def handle_help() -> Dict[str, Any]:
    """Handle help command"""
    return {
        'content': '''
        <div class="calendar-help">
            <h3>📅 Calendar Commands</h3>
            <div class="command-list">
                <p><strong>!calendar create</strong> "Title" "YYYY-MM-DD HH:MM" [description] [location] [max_attendees]</p>
                <p><strong>!calendar list</strong> [pending|approved|rejected] - List events</p>
                <p><strong>!calendar join</strong> [event_id] - Join an event</p>
                <p><strong>!calendar leave</strong> [event_id] - Leave an event</p>
                <p><strong>!calendar approve</strong> [event_id] - Approve pending event (admin/mod only)</p>
                <p><strong>!calendar reject</strong> [event_id] "reason" - Reject pending event (admin/mod only)</p>
                <p><strong>!calendar cancel</strong> [event_id] - Cancel event (creator only)</p>
            </div>
            <div class="calendar-info">
                <p><strong>Note:</strong> Users with the 'event-autoapprove' label can create events that are automatically approved.</p>
            </div>
        </div>
        '''
    }

if __name__ == '__main__':
    # Start the application
    from py4web import run
    run(port=MODULE_PORT, host='0.0.0.0')