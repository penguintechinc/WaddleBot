"""
Reputation service for handling reputation scoring logic
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from ..models import db, GLOBAL_COMMUNITY_NAME, GLOBAL_COMMUNITY_ID

logger = logging.getLogger(__name__)

class ReputationService:
    """Service for managing reputation scoring"""
    
    def __init__(self):
        self.global_community_id = GLOBAL_COMMUNITY_ID
        self.default_event_scores = {
            # Platform-agnostic events
            'message': 5,
            'reaction': 2,
            'member_join': 10,
            'member_leave': -5,
            'ban': -50,
            'kick': -25,
            'timeout': -10,
            'warn': -5,
            
            # Twitch-specific events
            'follow': 10,
            'sub': 50,
            'resub': 30,
            'subgift': 60,
            'raid': 30,
            'cheer': 1,  # 1 point per bit
            'host': 25,
            
            # Discord-specific events
            'voice_join': 8,
            'voice_leave': 0,
            'voice_time': 1,  # 1 point per minute
            'boost': 100,
            'thread_create': 15,
            'thread_reply': 8,
            'forum_post': 12,
            
            # Slack-specific events
            'file_share': 15,
            'app_mention': 8,
            'channel_join': 10,
            'workflow_step': 20,
            'reminder_set': 5,
        }
    
    def initialize_global_community(self) -> Dict[str, Any]:
        """Initialize the global community with default reputation scores"""
        try:
            # Check if global community already exists
            global_community = db(
                (db.communities.name == GLOBAL_COMMUNITY_NAME) &
                (db.communities.is_active == True)
            ).select().first()
            
            if not global_community:
                # Create global community
                community_id = db.communities.insert(
                    name=GLOBAL_COMMUNITY_NAME,
                    owners=["system"],
                    entity_groups=[],
                    member_ids=[],
                    description="Default global community for all users",
                    is_active=True,
                    settings={
                        'is_global': True,
                        'auto_join': True,
                        'public': True
                    },
                    created_by="system"
                )
                
                # Force the global community to have ID 1
                if community_id != GLOBAL_COMMUNITY_ID:
                    # Update the ID to be 1
                    db.executesql(
                        f"UPDATE communities SET id = {GLOBAL_COMMUNITY_ID} WHERE id = {community_id}"
                    )
                    # Update sequence for PostgreSQL
                    try:
                        db.executesql(
                            f"SELECT setval('communities_id_seq', {GLOBAL_COMMUNITY_ID})"
                        )
                    except:
                        pass  # SQLite doesn't have sequences
                
                global_community = db(db.communities.id == GLOBAL_COMMUNITY_ID).select().first()
                logger.info(f"Created global community with ID {GLOBAL_COMMUNITY_ID}")
            
            # Set up default reputation scores for global community
            self._setup_default_scores(GLOBAL_COMMUNITY_ID)
            
            db.commit()
            
            return {
                "community_id": GLOBAL_COMMUNITY_ID,
                "name": GLOBAL_COMMUNITY_NAME,
                "created": global_community.created_at,
                "default_scores_count": len(self.default_event_scores)
            }
            
        except Exception as e:
            logger.error(f"Error initializing global community: {str(e)}")
            raise
    
    def _setup_default_scores(self, community_id: int) -> None:
        """Set up default reputation scores for a community"""
        try:
            for event_name, event_score in self.default_event_scores.items():
                # Check if score already exists
                existing_score = db(
                    (db.reputation_scoring.community_id == community_id) &
                    (db.reputation_scoring.event_name == event_name) &
                    (db.reputation_scoring.is_active == True)
                ).select().first()
                
                if not existing_score:
                    db.reputation_scoring.insert(
                        event_name=event_name,
                        event_score=event_score,
                        community_id=community_id,
                        is_active=True,
                        description=f"Default score for {event_name} event",
                        created_by="system"
                    )
                    
            logger.info(f"Set up {len(self.default_event_scores)} default scores for community {community_id}")
            
        except Exception as e:
            logger.error(f"Error setting up default scores: {str(e)}")
            raise
    
    def get_community_for_entity(self, entity_id: str) -> Optional[int]:
        """Get the community ID for a given entity"""
        try:
            # First check if entity is in any entity group
            entity_group = db(
                (db.entity_groups.entity_ids.contains(entity_id)) &
                (db.entity_groups.is_active == True)
            ).select().first()
            
            if entity_group:
                return entity_group.community_id
            
            # Default to global community
            return GLOBAL_COMMUNITY_ID
            
        except Exception as e:
            logger.error(f"Error getting community for entity {entity_id}: {str(e)}")
            return GLOBAL_COMMUNITY_ID
    
    def get_user_communities(self, user_id: str) -> List[int]:
        """Get all communities a user belongs to"""
        try:
            communities = []
            
            # Get direct memberships
            memberships = db(
                (db.community_memberships.user_id == user_id) &
                (db.community_memberships.is_active == True)
            ).select()
            
            for membership in memberships:
                communities.append(membership.community_id)
            
            # All users are in global community
            if GLOBAL_COMMUNITY_ID not in communities:
                communities.append(GLOBAL_COMMUNITY_ID)
            
            return communities
            
        except Exception as e:
            logger.error(f"Error getting user communities for {user_id}: {str(e)}")
            return [GLOBAL_COMMUNITY_ID]
    
    def process_reputation_event(self, user_id: str, entity_id: str, event_name: str, 
                                event_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Process a reputation event for a user"""
        try:
            # Get the community for this entity
            community_id = self.get_community_for_entity(entity_id)
            
            # Get the score for this event in this community
            score_config = db(
                (db.reputation_scoring.community_id == community_id) &
                (db.reputation_scoring.event_name == event_name) &
                (db.reputation_scoring.is_active == True)
            ).select().first()
            
            if not score_config:
                logger.warning(f"No score configuration found for event {event_name} in community {community_id}")
                return {"success": False, "error": "No score configuration found"}
            
            event_score = score_config.event_score
            
            # Handle special cases (like cheer bits)
            if event_name == 'cheer' and event_data and 'bits' in event_data:
                event_score = event_data['bits']  # 1 point per bit
            elif event_name == 'voice_time' and event_data and 'minutes' in event_data:
                event_score = event_data['minutes']  # 1 point per minute
            
            # Get or create user reputation record
            user_rep = db(
                (db.user_reputation.user_id == user_id) &
                (db.user_reputation.community_id == community_id)
            ).select().first()
            
            if not user_rep:
                # Create new reputation record
                user_rep_id = db.user_reputation.insert(
                    user_id=user_id,
                    community_id=community_id,
                    current_score=0,
                    total_events=0,
                    last_activity=datetime.utcnow()
                )
                user_rep = db(db.user_reputation.id == user_rep_id).select().first()
            
            # Calculate new score
            previous_score = user_rep.current_score
            new_score = previous_score + event_score
            
            # Update user reputation
            db(db.user_reputation.id == user_rep.id).update(
                current_score=new_score,
                total_events=user_rep.total_events + 1,
                last_activity=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Log the event
            db.reputation_events.insert(
                user_id=user_id,
                community_id=community_id,
                entity_id=entity_id,
                event_name=event_name,
                event_score=event_score,
                previous_score=previous_score,
                new_score=new_score,
                event_data=event_data or {},
                processed_at=datetime.utcnow()
            )
            
            # Also process for global community if not already global
            if community_id != GLOBAL_COMMUNITY_ID:
                self.process_reputation_event(user_id, entity_id, event_name, event_data)
            
            db.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "community_id": community_id,
                "event_name": event_name,
                "event_score": event_score,
                "previous_score": previous_score,
                "new_score": new_score,
                "total_events": user_rep.total_events + 1
            }
            
        except Exception as e:
            logger.error(f"Error processing reputation event: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def get_user_reputation(self, user_id: str, community_id: Optional[int] = None) -> Dict[str, Any]:
        """Get user's reputation score(s)"""
        try:
            if community_id:
                # Get specific community reputation
                user_rep = db(
                    (db.user_reputation.user_id == user_id) &
                    (db.user_reputation.community_id == community_id)
                ).select().first()
                
                if not user_rep:
                    return {
                        "user_id": user_id,
                        "community_id": community_id,
                        "current_score": 0,
                        "total_events": 0,
                        "last_activity": None
                    }
                
                return {
                    "user_id": user_id,
                    "community_id": community_id,
                    "current_score": user_rep.current_score,
                    "total_events": user_rep.total_events,
                    "last_activity": user_rep.last_activity.isoformat() if user_rep.last_activity else None
                }
            else:
                # Get all community reputations for user
                user_reps = db(db.user_reputation.user_id == user_id).select()
                
                result = {
                    "user_id": user_id,
                    "communities": {}
                }
                
                for rep in user_reps:
                    community = db(db.communities.id == rep.community_id).select().first()
                    result["communities"][rep.community_id] = {
                        "community_name": community.name if community else "Unknown",
                        "current_score": rep.current_score,
                        "total_events": rep.total_events,
                        "last_activity": rep.last_activity.isoformat() if rep.last_activity else None
                    }
                
                return result
                
        except Exception as e:
            logger.error(f"Error getting user reputation: {str(e)}")
            return {"error": str(e)}
    
    def get_leaderboard(self, community_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get reputation leaderboard for a community"""
        try:
            top_users = db(
                db.user_reputation.community_id == community_id
            ).select(
                orderby=~db.user_reputation.current_score,
                limitby=(0, limit)
            )
            
            leaderboard = []
            for i, user_rep in enumerate(top_users, 1):
                leaderboard.append({
                    "rank": i,
                    "user_id": user_rep.user_id,
                    "current_score": user_rep.current_score,
                    "total_events": user_rep.total_events,
                    "last_activity": user_rep.last_activity.isoformat() if user_rep.last_activity else None
                })
            
            return leaderboard
            
        except Exception as e:
            logger.error(f"Error getting leaderboard: {str(e)}")
            return []