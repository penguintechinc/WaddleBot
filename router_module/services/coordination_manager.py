"""
Coordination manager for dynamic server/channel assignment across collector containers
Handles claiming, releasing, and managing distributed workloads
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from ..models import db, db_read

logger = logging.getLogger(__name__)

@dataclass
class ClaimResult:
    """Result of claiming operation"""
    success: bool
    claimed_entities: List[Dict]
    error_message: str = None

class CoordinationManager:
    """Manages coordination between collector containers"""
    
    def __init__(self, container_id: str = None, default_claim_limit: int = 5):
        self.container_id = container_id or self.generate_container_id()
        self.default_claim_limit = default_claim_limit
        self.claim_duration = timedelta(minutes=30)  # Claims expire after 30 minutes
        self.checkin_timeout = timedelta(minutes=6)   # Containers must checkin within 6 minutes
        self.checkin_interval = timedelta(minutes=5)  # Expected checkin every 5 minutes
        
        logger.info(f"CoordinationManager initialized with container_id: {self.container_id}")
    
    def generate_container_id(self) -> str:
        """Generate unique container ID"""
        return f"container_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
    
    async def claim_entities(self, platform: str, max_claims: int = None) -> ClaimResult:
        """Claim available entities for this container"""
        try:
            max_claims = max_claims or self.default_claim_limit
            
            # First, clean up expired claims
            await self.cleanup_expired_claims()
            
            # Get available entities, prioritizing live channels
            available_entities = await self.get_available_entities(platform, max_claims)
            
            if not available_entities:
                return ClaimResult(
                    success=True,
                    claimed_entities=[],
                    error_message="No available entities to claim"
                )
            
            # Claim the entities atomically
            claimed_entities = []
            claim_time = datetime.utcnow()
            claim_expires = claim_time + self.claim_duration
            
            for entity in available_entities:
                try:
                    # Atomic claim update
                    updated = db.executesql("""
                        UPDATE coordination 
                        SET claimed_by = %s, 
                            claimed_at = %s, 
                            claim_expires = %s,
                            last_checkin = %s,
                            status = 'claimed',
                            updated_at = %s
                        WHERE id = %s 
                        AND (claimed_by IS NULL OR claim_expires < %s OR last_checkin < %s)
                    """, [
                        self.container_id,
                        claim_time,
                        claim_expires,
                        claim_time,
                        claim_time,
                        entity['id'],
                        claim_time,
                        claim_time - self.checkin_timeout
                    ])
                    
                    if updated:
                        entity['claimed_by'] = self.container_id
                        entity['claimed_at'] = claim_time
                        entity['claim_expires'] = claim_expires
                        entity['status'] = 'claimed'
                        claimed_entities.append(entity)
                        
                        logger.info(f"Claimed entity {entity['entity_id']} for container {self.container_id}")
                    
                except Exception as e:
                    logger.error(f"Error claiming entity {entity['id']}: {str(e)}")
                    continue
            
            db.commit()
            
            return ClaimResult(
                success=True,
                claimed_entities=claimed_entities
            )
            
        except Exception as e:
            logger.error(f"Error claiming entities for platform {platform}: {str(e)}")
            return ClaimResult(
                success=False,
                claimed_entities=[],
                error_message=str(e)
            )
    
    async def get_available_entities(self, platform: str, limit: int) -> List[Dict]:
        """Get available entities for claiming, prioritizing live channels"""
        try:
            # Query for available entities, prioritizing live channels and then by priority
            current_time = datetime.utcnow()
            checkin_deadline = current_time - self.checkin_timeout
            
            entities = db_read(
                (db_read.coordination.platform == platform) &
                ((db_read.coordination.claimed_by == None) | 
                 (db_read.coordination.claim_expires < current_time) |
                 (db_read.coordination.last_checkin < checkin_deadline)) &
                (db_read.coordination.status.belongs(['available', 'live', 'offline']))
            ).select(
                orderby=(~db_read.coordination.is_live, 
                        db_read.coordination.priority, 
                        ~db_read.coordination.viewer_count,
                        db_read.coordination.last_activity),
                limitby=(0, limit * 2)  # Get more than needed in case of race conditions
            )
            
            available_list = []
            for entity in entities:
                # Double-check availability
                if (not entity.claimed_by or 
                    entity.claim_expires < current_time or
                    (entity.last_checkin and entity.last_checkin < checkin_deadline)):
                    available_list.append(dict(entity))
                    
                    if len(available_list) >= limit:
                        break
            
            return available_list
            
        except Exception as e:
            logger.error(f"Error getting available entities: {str(e)}")
            return []
    
    async def release_entities(self, entity_ids: List[str] = None) -> bool:
        """Release claimed entities"""
        try:
            if entity_ids:
                # Release specific entities
                query = (
                    (db.coordination.claimed_by == self.container_id) &
                    (db.coordination.entity_id.belongs(entity_ids))
                )
            else:
                # Release all entities claimed by this container
                query = (db.coordination.claimed_by == self.container_id)
            
            db(query).update(
                claimed_by=None,
                claimed_at=None,
                claim_expires=None,
                status='available',
                updated_at=datetime.utcnow()
            )
            db.commit()
            
            logger.info(f"Released entities for container {self.container_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing entities: {str(e)}")
            return False
    
    async def checkin(self) -> bool:
        """Check in to maintain claims and extend expiration"""
        try:
            current_time = datetime.utcnow()
            new_expires = current_time + self.claim_duration
            
            # Update checkin time and extend claims for all entities claimed by this container
            updated_count = db(
                db.coordination.claimed_by == self.container_id
            ).update(
                last_checkin=current_time,
                claim_expires=new_expires,
                updated_at=current_time
            )
            db.commit()
            
            logger.debug(f"Checked in for {updated_count} entities")
            return True
            
        except Exception as e:
            logger.error(f"Error during checkin: {str(e)}")
            return False
    
    async def update_entity_status(self, entity_id: str, is_live: bool = None, 
                                 viewer_count: int = None, metadata: Dict = None,
                                 has_activity: bool = False) -> bool:
        """Update status of a claimed entity"""
        try:
            current_time = datetime.utcnow()
            update_data = {
                'last_check': current_time,
                'last_checkin': current_time,  # Update checkin time when updating status
                'updated_at': current_time
            }
            
            if is_live is not None:
                update_data['is_live'] = is_live
                if is_live and not db_read(
                    (db_read.coordination.entity_id == entity_id) & 
                    (db_read.coordination.is_live == True)
                ).select().first():
                    update_data['live_since'] = current_time
                    update_data['status'] = 'live'
                elif not is_live:
                    update_data['live_since'] = None
                    update_data['status'] = 'offline'
            
            if viewer_count is not None:
                update_data['viewer_count'] = viewer_count
            
            if metadata is not None:
                update_data['metadata'] = metadata
            
            if has_activity:
                update_data['last_activity'] = current_time
                update_data['error_count'] = 0
            
            db(
                (db.coordination.entity_id == entity_id) &
                (db.coordination.claimed_by == self.container_id)
            ).update(**update_data)
            db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating entity status for {entity_id}: {str(e)}")
            return False
    
    async def release_offline_entities(self) -> List[str]:
        """Release entities that have gone offline and claim new ones"""
        try:
            # Find offline entities claimed by this container
            offline_entities = db_read(
                (db_read.coordination.claimed_by == self.container_id) &
                (db_read.coordination.is_live == False) &
                (db_read.coordination.status == 'offline')
            ).select()
            
            released_entity_ids = []
            
            for entity in offline_entities:
                # Release the offline entity
                db(
                    (db.coordination.entity_id == entity.entity_id) &
                    (db.coordination.claimed_by == self.container_id)
                ).update(
                    claimed_by=None,
                    claimed_at=None,
                    claim_expires=None,
                    last_checkin=None,
                    status='available',
                    updated_at=datetime.utcnow()
                )
                
                released_entity_ids.append(entity.entity_id)
                logger.info(f"Released offline entity: {entity.entity_id}")
            
            if released_entity_ids:
                db.commit()
                
                # Try to claim new entities to replace the offline ones
                platform = offline_entities[0].platform if offline_entities else None
                if platform:
                    await self.claim_entities(platform, len(released_entity_ids))
            
            return released_entity_ids
            
        except Exception as e:
            logger.error(f"Error releasing offline entities: {str(e)}")
            return []
    
    async def report_error(self, entity_id: str, error_message: str) -> bool:
        """Report error for an entity"""
        try:
            # Get current entity
            entity = db_read(
                (db_read.coordination.entity_id == entity_id) &
                (db_read.coordination.claimed_by == self.container_id)
            ).select().first()
            
            if not entity:
                return False
            
            error_count = entity.error_count + 1
            status = 'error' if error_count >= 3 else entity.status
            
            db(
                (db.coordination.entity_id == entity_id) &
                (db.coordination.claimed_by == self.container_id)
            ).update(
                error_count=error_count,
                status=status,
                last_check=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.commit()
            
            logger.warning(f"Error reported for entity {entity_id}: {error_message} (count: {error_count})")
            return True
            
        except Exception as e:
            logger.error(f"Error reporting error for entity {entity_id}: {str(e)}")
            return False
    
    async def heartbeat(self, extend_claims: bool = True) -> Dict:
        """Send heartbeat and optionally extend claim duration"""
        try:
            claimed_entities = db_read(
                db_read.coordination.claimed_by == self.container_id
            ).select()
            
            heartbeat_data = {
                'container_id': self.container_id,
                'timestamp': datetime.utcnow().isoformat(),
                'claimed_count': len(claimed_entities),
                'entities': []
            }
            
            if extend_claims:
                new_expires = datetime.utcnow() + self.claim_duration
                
                db(db.coordination.claimed_by == self.container_id).update(
                    claim_expires=new_expires,
                    last_check=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.commit()
            
            for entity in claimed_entities:
                heartbeat_data['entities'].append({
                    'entity_id': entity.entity_id,
                    'platform': entity.platform,
                    'status': entity.status,
                    'is_live': entity.is_live,
                    'viewer_count': entity.viewer_count,
                    'last_activity': entity.last_activity.isoformat() if entity.last_activity else None
                })
            
            logger.debug(f"Heartbeat sent for container {self.container_id}: {len(claimed_entities)} entities")
            return heartbeat_data
            
        except Exception as e:
            logger.error(f"Error sending heartbeat: {str(e)}")
            return {'error': str(e)}
    
    async def cleanup_expired_claims(self) -> int:
        """Clean up expired claims and missed checkins"""
        try:
            current_time = datetime.utcnow()
            checkin_deadline = current_time - self.checkin_timeout
            
            # Find expired claims (either by expiration time or missed checkin)
            expired_claims = db(
                (db.coordination.claimed_by != None) &
                ((db.coordination.claim_expires < current_time) |
                 (db.coordination.last_checkin < checkin_deadline))
            ).select()
            
            if expired_claims:
                expired_by_timeout = [c for c in expired_claims if c.claim_expires < current_time]
                expired_by_checkin = [c for c in expired_claims if c.last_checkin and c.last_checkin < checkin_deadline]
                
                # Release expired claims
                db(
                    (db.coordination.claimed_by != None) &
                    ((db.coordination.claim_expires < current_time) |
                     (db.coordination.last_checkin < checkin_deadline))
                ).update(
                    claimed_by=None,
                    claimed_at=None,
                    claim_expires=None,
                    last_checkin=None,
                    status='available',
                    updated_at=current_time
                )
                db.commit()
                
                logger.info(f"Cleaned up {len(expired_claims)} expired claims "
                          f"({len(expired_by_timeout)} by timeout, {len(expired_by_checkin)} by missed checkin)")
                return len(expired_claims)
            
            return 0
            
        except Exception as e:
            logger.error(f"Error cleaning up expired claims: {str(e)}")
            return 0
    
    async def get_claimed_entities(self) -> List[Dict]:
        """Get entities currently claimed by this container"""
        try:
            entities = db_read(
                db_read.coordination.claimed_by == self.container_id
            ).select(orderby=db_read.coordination.priority)
            
            return [dict(entity) for entity in entities]
            
        except Exception as e:
            logger.error(f"Error getting claimed entities: {str(e)}")
            return []
    
    async def populate_from_servers_table(self, platform: str) -> int:
        """Populate coordination table from existing servers table"""
        try:
            # Get servers for this platform
            servers = db_read(
                (db_read.servers.platform == platform) &
                (db_read.servers.is_active == True)
            ).select()
            
            inserted_count = 0
            
            for server in servers:
                # Generate entity_id
                if server.channel:
                    entity_id = f"{platform}:{server.server_id or server.channel}:{server.channel}"
                else:
                    entity_id = f"{platform}:{server.server_id or server.channel}"
                
                # Check if already exists
                existing = db_read(
                    db_read.coordination.entity_id == entity_id
                ).select().first()
                
                if not existing:
                    db.coordination.insert(
                        platform=platform,
                        server_id=server.server_id or server.channel,
                        channel_id=server.channel if server.server_id else None,
                        entity_id=entity_id,
                        status='available',
                        priority=100,
                        config=server.config
                    )
                    inserted_count += 1
            
            db.commit()
            logger.info(f"Populated {inserted_count} entities for platform {platform}")
            return inserted_count
            
        except Exception as e:
            logger.error(f"Error populating coordination table: {str(e)}")
            return 0
    
    def get_stats(self) -> Dict:
        """Get coordination statistics"""
        try:
            total_entities = db(db.coordination.id > 0).count()
            claimed_entities = db(db.coordination.claimed_by != None).count()
            live_entities = db(db.coordination.is_live == True).count()
            error_entities = db(db.coordination.status == 'error').count()
            
            container_stats = db().select(
                db.coordination.claimed_by,
                db.coordination.id.count(),
                groupby=db.coordination.claimed_by,
                having=(db.coordination.claimed_by != None)
            )
            
            return {
                'total_entities': total_entities,
                'claimed_entities': claimed_entities,
                'available_entities': total_entities - claimed_entities,
                'live_entities': live_entities,
                'error_entities': error_entities,
                'containers': {
                    row.coordination.claimed_by: row._extra[db.coordination.id.count()]
                    for row in container_stats
                },
                'this_container': {
                    'container_id': self.container_id,
                    'claimed_count': db(db.coordination.claimed_by == self.container_id).count()
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting coordination stats: {str(e)}")
            return {'error': str(e)}

# Global coordination manager instance
coordination_manager = None

def get_coordination_manager(container_id: str = None, claim_limit: int = 5) -> CoordinationManager:
    """Get or create coordination manager instance"""
    global coordination_manager
    if coordination_manager is None:
        coordination_manager = CoordinationManager(container_id, claim_limit)
    return coordination_manager