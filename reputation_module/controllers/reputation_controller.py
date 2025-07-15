"""
Reputation controller for handling reputation-related requests
"""

import logging
from py4web import action, request, response, HTTP
from typing import Dict, Any

from ..services.reputation_service import ReputationService
from ..models import db

logger = logging.getLogger(__name__)

# Initialize reputation service
reputation_service = ReputationService()

@action("reputation/process", method=["POST"])
def process_reputation_event():
    """Process a reputation event"""
    try:
        event_data = request.json
        if not event_data:
            raise HTTP(400, "No event data provided")
        
        # Validate required fields
        required_fields = ["user_id", "entity_id", "event_name"]
        missing_fields = [field for field in required_fields if field not in event_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        # Process the event
        result = reputation_service.process_reputation_event(
            user_id=event_data["user_id"],
            entity_id=event_data["entity_id"],
            event_name=event_data["event_name"],
            event_data=event_data.get("event_data", {})
        )
        
        if result["success"]:
            return result
        else:
            raise HTTP(400, result.get("error", "Failed to process reputation event"))
            
    except Exception as e:
        logger.error(f"Error processing reputation event: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("reputation/user/<user_id>", method=["GET"])
def get_user_reputation(user_id: str):
    """Get user's reputation scores"""
    try:
        community_id = request.query.get("community_id")
        if community_id:
            try:
                community_id = int(community_id)
            except ValueError:
                raise HTTP(400, "Invalid community_id format")
        
        result = reputation_service.get_user_reputation(user_id, community_id)
        
        if "error" in result:
            raise HTTP(500, result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting user reputation: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("reputation/leaderboard/<community_id:int>", method=["GET"])
def get_leaderboard(community_id: int):
    """Get reputation leaderboard for a community"""
    try:
        limit = int(request.query.get("limit", 10))
        if limit > 100:
            limit = 100  # Cap at 100 for performance
        
        leaderboard = reputation_service.get_leaderboard(community_id, limit)
        
        return {
            "community_id": community_id,
            "limit": limit,
            "leaderboard": leaderboard
        }
        
    except Exception as e:
        logger.error(f"Error getting leaderboard: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("reputation/events/<user_id>", method=["GET"])
def get_user_events(user_id: str):
    """Get recent reputation events for a user"""
    try:
        community_id = request.query.get("community_id")
        limit = int(request.query.get("limit", 50))
        
        if limit > 200:
            limit = 200  # Cap at 200 for performance
        
        # Build query
        query = db.reputation_events.user_id == user_id
        
        if community_id:
            try:
                community_id = int(community_id)
                query &= db.reputation_events.community_id == community_id
            except ValueError:
                raise HTTP(400, "Invalid community_id format")
        
        # Get events
        events = db(query).select(
            orderby=~db.reputation_events.processed_at,
            limitby=(0, limit)
        )
        
        # Format response
        event_list = []
        for event in events:
            event_list.append({
                "id": event.id,
                "event_name": event.event_name,
                "event_score": event.event_score,
                "previous_score": event.previous_score,
                "new_score": event.new_score,
                "entity_id": event.entity_id,
                "community_id": event.community_id,
                "event_data": event.event_data,
                "processed_at": event.processed_at.isoformat()
            })
        
        return {
            "user_id": user_id,
            "community_id": community_id,
            "events": event_list,
            "total": len(event_list)
        }
        
    except Exception as e:
        logger.error(f"Error getting user events: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("reputation/scoring/<community_id:int>", method=["GET"])
def get_community_scoring(community_id: int):
    """Get reputation scoring configuration for a community"""
    try:
        scoring_rules = db(
            (db.reputation_scoring.community_id == community_id) &
            (db.reputation_scoring.is_active == True)
        ).select(orderby=db.reputation_scoring.event_name)
        
        rules = []
        for rule in scoring_rules:
            rules.append({
                "id": rule.id,
                "event_name": rule.event_name,
                "event_score": rule.event_score,
                "description": rule.description,
                "created_by": rule.created_by,
                "created_at": rule.created_at.isoformat()
            })
        
        return {
            "community_id": community_id,
            "scoring_rules": rules,
            "total": len(rules)
        }
        
    except Exception as e:
        logger.error(f"Error getting community scoring: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("reputation/scoring/<community_id:int>", method=["POST"])
def update_community_scoring(community_id: int):
    """Update reputation scoring configuration for a community"""
    try:
        scoring_data = request.json
        if not scoring_data:
            raise HTTP(400, "No scoring data provided")
        
        # Validate required fields
        required_fields = ["event_name", "event_score"]
        missing_fields = [field for field in required_fields if field not in scoring_data]
        if missing_fields:
            raise HTTP(400, f"Missing required fields: {', '.join(missing_fields)}")
        
        # Check if rule already exists
        existing_rule = db(
            (db.reputation_scoring.community_id == community_id) &
            (db.reputation_scoring.event_name == scoring_data["event_name"]) &
            (db.reputation_scoring.is_active == True)
        ).select().first()
        
        if existing_rule:
            # Update existing rule
            db(db.reputation_scoring.id == existing_rule.id).update(
                event_score=scoring_data["event_score"],
                description=scoring_data.get("description", existing_rule.description),
                updated_at=datetime.utcnow()
            )
            rule_id = existing_rule.id
        else:
            # Create new rule
            rule_id = db.reputation_scoring.insert(
                event_name=scoring_data["event_name"],
                event_score=scoring_data["event_score"],
                community_id=community_id,
                description=scoring_data.get("description", ""),
                created_by=scoring_data.get("created_by", "system"),
                is_active=True
            )
        
        db.commit()
        
        # Return the updated rule
        rule = db(db.reputation_scoring.id == rule_id).select().first()
        
        return {
            "success": True,
            "rule": {
                "id": rule.id,
                "event_name": rule.event_name,
                "event_score": rule.event_score,
                "description": rule.description,
                "community_id": rule.community_id,
                "created_by": rule.created_by,
                "created_at": rule.created_at.isoformat(),
                "updated_at": rule.updated_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Error updating community scoring: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")

@action("reputation/stats/<community_id:int>", method=["GET"])
def get_community_stats(community_id: int):
    """Get reputation statistics for a community"""
    try:
        # Get basic stats
        total_users = db(db.user_reputation.community_id == community_id).count()
        total_events = db(db.reputation_events.community_id == community_id).count()
        
        # Get score distribution
        score_stats = db(db.user_reputation.community_id == community_id).select(
            db.user_reputation.current_score.avg(),
            db.user_reputation.current_score.min(),
            db.user_reputation.current_score.max(),
            db.user_reputation.current_score.sum()
        ).first()
        
        # Get top events
        top_events = db(db.reputation_events.community_id == community_id).select(
            db.reputation_events.event_name,
            db.reputation_events.event_name.count().with_alias('count'),
            groupby=db.reputation_events.event_name,
            orderby=~db.reputation_events.event_name.count(),
            limitby=(0, 10)
        )
        
        event_stats = []
        for event in top_events:
            event_stats.append({
                "event_name": event.reputation_events.event_name,
                "count": event.count
            })
        
        return {
            "community_id": community_id,
            "total_users": total_users,
            "total_events": total_events,
            "score_stats": {
                "average": float(score_stats.avg) if score_stats.avg else 0,
                "minimum": score_stats.min if score_stats.min else 0,
                "maximum": score_stats.max if score_stats.max else 0,
                "total": score_stats.sum if score_stats.sum else 0
            },
            "top_events": event_stats
        }
        
    except Exception as e:
        logger.error(f"Error getting community stats: {str(e)}")
        raise HTTP(500, f"Internal server error: {str(e)}")