"""
Giveaway Service with Reputation Integration
Manages giveaways with reputation-weighted entries, shadow banning,
game key distribution, and multi-winner support.
"""
import logging
import random
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class GiveawayInfo:
    """Giveaway information"""
    id: int
    community_id: int
    title: str
    description: str
    prize_description: str
    entry_cost: int
    max_entries_per_user: int
    reputation_floor: int
    weighted_by_reputation: bool
    status: str
    starts_at: datetime
    ends_at: datetime
    entry_count: int = 0


class GiveawayService:
    """
    Giveaway management with reputation integration.

    Features:
    - Free or currency-cost entries
    - Reputation floor for eligibility
    - Shadow banning (below-floor users can enter but never win)
    - Weighted odds by reputation tier
    """

    REPUTATION_WEIGHTS = {
        'exceptional': 1.5,   # 800-850
        'very_good': 1.25,    # 740-799
        'good': 1.1,          # 670-739
        'fair': 1.0,          # 580-669
        'poor': 0.75,         # 300-579
    }

    # Game key format patterns per platform
    KEY_PATTERNS = {
        'steam': re.compile(r'^[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}$'),
        'epic': re.compile(r'^[A-Z0-9]{13,}$'),
        'gog': re.compile(r'^[A-Z0-9]{14,}$'),
    }

    def __init__(self, dal, currency_service, reputation_api_url: str = None):
        self.dal = dal
        self.currency_service = currency_service
        self.reputation_api_url = reputation_api_url

    async def create_giveaway(
        self,
        community_id: int,
        title: str,
        prize_description: str,
        created_by: int,
        description: str = None,
        entry_cost: int = 0,
        max_entries_per_user: int = 1,
        reputation_floor: int = 450,
        weighted_by_reputation: bool = False,
        starts_at: datetime = None,
        ends_at: datetime = None
    ) -> Optional[int]:
        """Create a new giveaway."""
        try:
            query = """
                INSERT INTO loyalty_giveaways
                    (community_id, title, description, prize_description, entry_cost,
                     max_entries_per_user, reputation_floor, weighted_by_reputation,
                     status, starts_at, ends_at, created_by)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                RETURNING id
            """
            result = await self.dal.execute(query, [
                community_id, title, description, prize_description, entry_cost,
                max_entries_per_user, reputation_floor, weighted_by_reputation,
                'draft', starts_at, ends_at, created_by
            ])
            return result[0]['id'] if result else None

        except Exception as e:
            logger.error(f"Error creating giveaway: {e}")
            return None

    async def get_active_giveaway(self, community_id: int) -> Optional[GiveawayInfo]:
        """Get the currently active giveaway for a community."""
        try:
            query = """
                SELECT g.*, COUNT(e.id) as entry_count
                FROM loyalty_giveaways g
                LEFT JOIN loyalty_giveaway_entries e ON g.id = e.giveaway_id
                WHERE g.community_id = $1 AND g.status = 'active'
                  AND (g.starts_at IS NULL OR g.starts_at <= NOW())
                  AND (g.ends_at IS NULL OR g.ends_at > NOW())
                GROUP BY g.id
                LIMIT 1
            """
            rows = await self.dal.execute(query, [community_id])

            if rows and len(rows) > 0:
                row = rows[0]
                return GiveawayInfo(
                    id=row['id'],
                    community_id=row['community_id'],
                    title=row['title'],
                    description=row['description'],
                    prize_description=row['prize_description'],
                    entry_cost=row['entry_cost'],
                    max_entries_per_user=row['max_entries_per_user'],
                    reputation_floor=row['reputation_floor'],
                    weighted_by_reputation=row['weighted_by_reputation'],
                    status=row['status'],
                    starts_at=row['starts_at'],
                    ends_at=row['ends_at'],
                    entry_count=row['entry_count']
                )
            return None

        except Exception as e:
            logger.error(f"Error getting active giveaway: {e}")
            return None

    async def _get_user_reputation(
        self,
        community_id: int,
        platform: str,
        platform_user_id: str
    ) -> Dict[str, Any]:
        """Fetch user reputation from reputation module."""
        if not self.reputation_api_url:
            return {'score': 600, 'tier': 'fair'}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.reputation_api_url}/api/v1/reputation/{community_id}/user/{platform}/{platform_user_id}",
                    timeout=5.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'score': data.get('score', 600),
                        'tier': data.get('tier', 'fair')
                    }
        except Exception as e:
            logger.warning(f"Failed to fetch reputation: {e}")

        return {'score': 600, 'tier': 'fair'}

    def _get_reputation_tier(self, score: int) -> str:
        """Get reputation tier from score."""
        if score >= 800:
            return 'exceptional'
        elif score >= 740:
            return 'very_good'
        elif score >= 670:
            return 'good'
        elif score >= 580:
            return 'fair'
        return 'poor'

    async def enter_giveaway(
        self,
        giveaway_id: int,
        platform: str,
        platform_user_id: str,
        platform_username: str = None,
        hub_user_id: int = None
    ) -> Dict[str, Any]:
        """
        Enter a user into a giveaway.

        Returns dict with success status and message.
        Shadow-banned users (below reputation floor) can enter but are marked.
        """
        try:
            # Get giveaway
            query = "SELECT * FROM loyalty_giveaways WHERE id = $1"
            rows = await self.dal.execute(query, [giveaway_id])
            if not rows:
                return {'success': False, 'message': 'Giveaway not found'}

            giveaway = rows[0]

            if giveaway['status'] != 'active':
                return {'success': False, 'message': 'Giveaway is not active'}

            # Check existing entries
            entry_query = """
                SELECT entry_count FROM loyalty_giveaway_entries
                WHERE giveaway_id = $1 AND platform = $2 AND platform_user_id = $3
            """
            existing = await self.dal.execute(entry_query, [giveaway_id, platform, platform_user_id])

            current_entries = existing[0]['entry_count'] if existing else 0
            if current_entries >= giveaway['max_entries_per_user']:
                return {'success': False, 'message': 'Maximum entries reached'}

            # Charge entry cost if applicable
            if giveaway['entry_cost'] > 0:
                result = await self.currency_service.remove_currency(
                    giveaway['community_id'], platform, platform_user_id,
                    giveaway['entry_cost'], 'giveaway_entry',
                    f"Entry for giveaway: {giveaway['title']}"
                )
                if not result.success:
                    return {'success': False, 'message': result.message}

            # Get reputation
            rep_data = await self._get_user_reputation(
                giveaway['community_id'], platform, platform_user_id
            )
            rep_score = rep_data['score']
            rep_tier = self._get_reputation_tier(rep_score)
            is_shadow_banned = rep_score < giveaway['reputation_floor']

            # Calculate weight multiplier
            weight = self.REPUTATION_WEIGHTS.get(rep_tier, 1.0) if giveaway['weighted_by_reputation'] else 1.0

            # Insert or update entry
            if existing:
                update_query = """
                    UPDATE loyalty_giveaway_entries
                    SET entry_count = entry_count + 1
                    WHERE giveaway_id = $1 AND platform = $2 AND platform_user_id = $3
                """
                await self.dal.execute(update_query, [giveaway_id, platform, platform_user_id])
            else:
                insert_query = """
                    INSERT INTO loyalty_giveaway_entries
                        (giveaway_id, hub_user_id, platform, platform_user_id, platform_username,
                         reputation_score, reputation_tier, is_shadow_banned, weight_multiplier)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """
                await self.dal.execute(insert_query, [
                    giveaway_id, hub_user_id, platform, platform_user_id, platform_username,
                    rep_score, rep_tier, is_shadow_banned, weight
                ])

            return {
                'success': True,
                'message': 'Entered successfully!' if not is_shadow_banned else 'Entered successfully!',
                'entries': current_entries + 1,
                'is_shadow_banned': is_shadow_banned  # Don't expose this to user
            }

        except Exception as e:
            logger.error(f"Error entering giveaway: {e}")
            return {'success': False, 'message': 'Failed to enter giveaway'}

    async def draw_winner(self, giveaway_id: int) -> Optional[Dict[str, Any]]:
        """
        Draw a winner using weighted random selection.
        Shadow-banned users are excluded from winning.
        """
        try:
            # Get eligible entries (not shadow banned)
            query = """
                SELECT * FROM loyalty_giveaway_entries
                WHERE giveaway_id = $1 AND is_shadow_banned = FALSE
            """
            entries = await self.dal.execute(query, [giveaway_id])

            if not entries:
                return None

            # Build weighted pool
            weighted_pool = []
            for entry in entries:
                weight = float(entry['weight_multiplier']) * entry['entry_count']
                weighted_pool.extend([entry] * int(weight * 100))

            if not weighted_pool:
                return None

            # Draw winner
            winner = random.choice(weighted_pool)

            # Update giveaway
            update_query = """
                UPDATE loyalty_giveaways
                SET status = 'completed',
                    winner_user_id = $1,
                    winner_platform = $2,
                    winner_platform_user_id = $3,
                    updated_at = NOW()
                WHERE id = $4
            """
            await self.dal.execute(update_query, [
                winner['hub_user_id'], winner['platform'],
                winner['platform_user_id'], giveaway_id
            ])

            logger.info(f"Giveaway {giveaway_id} winner: {winner['platform']}:{winner['platform_user_id']}")

            return {
                'platform': winner['platform'],
                'platform_user_id': winner['platform_user_id'],
                'platform_username': winner['platform_username']
            }

        except Exception as e:
            logger.error(f"Error drawing winner: {e}")
            return None

    async def list_giveaways(
        self,
        community_id: int,
        status: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """List giveaways for a community."""
        try:
            if status:
                query = """
                    SELECT g.*, COUNT(e.id) as entry_count
                    FROM loyalty_giveaways g
                    LEFT JOIN loyalty_giveaway_entries e ON g.id = e.giveaway_id
                    WHERE g.community_id = $1 AND g.status = $2
                    GROUP BY g.id
                    ORDER BY g.created_at DESC
                    LIMIT $3
                """
                rows = await self.dal.execute(query, [community_id, status, limit])
            else:
                query = """
                    SELECT g.*, COUNT(e.id) as entry_count
                    FROM loyalty_giveaways g
                    LEFT JOIN loyalty_giveaway_entries e ON g.id = e.giveaway_id
                    WHERE g.community_id = $1
                    GROUP BY g.id
                    ORDER BY g.created_at DESC
                    LIMIT $2
                """
                rows = await self.dal.execute(query, [community_id, limit])

            return [dict(row) for row in (rows or [])]

        except Exception as e:
            logger.error(f"Error listing giveaways: {e}")
            return []

    # =========================================================================
    # Game Key Giveaway Methods
    # =========================================================================

    def _validate_key(self, key: str, platform: str = None) -> bool:
        """Validate a game key format for a given platform."""
        if not key or len(key) < 5:
            return False
        if platform and platform in self.KEY_PATTERNS:
            return bool(self.KEY_PATTERNS[platform].match(key.strip().upper()))
        return True  # Accept unknown platforms

    async def create_key_giveaway(
        self,
        community_id: int,
        title: str,
        prize_description: str,
        created_by: int,
        key_platform: str = None,
        winner_count: int = 1,
        description: str = None,
        entry_cost: int = 0,
        max_entries_per_user: int = 1,
        reputation_floor: int = 450,
        weighted_by_reputation: bool = False,
        sub_only: bool = False,
        min_account_age_days: int = 0,
        loyalty_threshold: int = 0,
        starts_at: datetime = None,
        ends_at: datetime = None,
        notification_message: str = None,
    ) -> Optional[int]:
        """Create a game key giveaway with enhanced eligibility options."""
        try:
            query = """
                INSERT INTO loyalty_giveaways
                    (community_id, title, description, prize_description, entry_cost,
                     max_entries_per_user, reputation_floor, weighted_by_reputation,
                     status, starts_at, ends_at, created_by,
                     giveaway_type, sub_only, min_account_age_days,
                     loyalty_threshold, winner_count, key_platform,
                     notification_message)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12,
                        $13, $14, $15, $16, $17, $18, $19)
                RETURNING id
            """
            result = await self.dal.execute(query, [
                community_id, title, description, prize_description, entry_cost,
                max_entries_per_user, reputation_floor, weighted_by_reputation,
                'draft', starts_at, ends_at, created_by,
                'game_key', sub_only, min_account_age_days,
                loyalty_threshold, winner_count, key_platform,
                notification_message,
            ])
            return result[0]['id'] if result else None

        except Exception as e:
            logger.error(f"Error creating key giveaway: {e}")
            return None

    async def add_keys(
        self,
        giveaway_id: int,
        keys: List[str],
        key_platform: str = None,
    ) -> Dict[str, Any]:
        """Batch add game keys to a giveaway with format validation."""
        added = 0
        invalid = []

        for key in keys:
            key = key.strip()
            if not self._validate_key(key, key_platform):
                invalid.append(key)
                continue

            try:
                await self.dal.execute(
                    """
                    INSERT INTO loyalty_giveaway_keys
                        (giveaway_id, key_value, key_platform)
                    VALUES ($1, $2, $3)
                    """,
                    [giveaway_id, key, key_platform],
                )
                added += 1
            except Exception as e:
                logger.warning(f"Failed to add key: {e}")
                invalid.append(key)

        return {
            'success': True,
            'added': added,
            'invalid': len(invalid),
            'total_submitted': len(keys),
        }

    async def get_key_count(self, giveaway_id: int) -> Dict[str, int]:
        """Get count of total and unclaimed keys for a giveaway."""
        try:
            rows = await self.dal.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE is_valid = TRUE) as total_valid,
                    COUNT(*) FILTER (WHERE is_claimed = FALSE AND is_valid = TRUE) as unclaimed
                FROM loyalty_giveaway_keys
                WHERE giveaway_id = $1
                """,
                [giveaway_id],
            )
            row = rows[0] if rows else {}
            return {
                'total_valid': row.get('total_valid', 0),
                'unclaimed': row.get('unclaimed', 0),
            }
        except Exception as e:
            logger.error(f"Error getting key count: {e}")
            return {'total_valid': 0, 'unclaimed': 0}

    async def check_eligibility(
        self,
        giveaway_id: int,
        community_id: int,
        platform: str,
        platform_user_id: str,
        is_subscriber: bool = False,
        account_age_days: int = 0,
        loyalty_points: int = 0,
    ) -> Dict[str, Any]:
        """Check if a user meets all eligibility requirements."""
        try:
            rows = await self.dal.execute(
                "SELECT * FROM loyalty_giveaways WHERE id = $1 AND community_id = $2",
                [giveaway_id, community_id],
            )
            if not rows:
                return {'eligible': False, 'reason': 'Giveaway not found'}

            giveaway = rows[0]

            if giveaway['sub_only'] and not is_subscriber:
                return {'eligible': False, 'reason': 'Subscribers only'}

            min_age = giveaway.get('min_account_age_days', 0)
            if min_age and account_age_days < min_age:
                return {
                    'eligible': False,
                    'reason': f'Account must be at least {min_age} days old',
                }

            threshold = giveaway.get('loyalty_threshold', 0)
            if threshold and loyalty_points < threshold:
                return {
                    'eligible': False,
                    'reason': f'Need at least {threshold} loyalty points',
                }

            return {'eligible': True, 'reason': None}

        except Exception as e:
            logger.error(f"Error checking eligibility: {e}")
            return {'eligible': False, 'reason': 'Internal error'}

    async def draw_winners(
        self,
        giveaway_id: int,
        count: int = None,
    ) -> List[Dict[str, Any]]:
        """
        Draw multiple winners using weighted random selection.
        Respects winner_count from giveaway config if count not specified.
        """
        try:
            # Get giveaway config
            giveaway_rows = await self.dal.execute(
                "SELECT * FROM loyalty_giveaways WHERE id = $1",
                [giveaway_id],
            )
            if not giveaway_rows:
                return []

            giveaway = giveaway_rows[0]
            num_winners = count or giveaway.get('winner_count', 1)

            # Get eligible entries (not shadow banned)
            entries = await self.dal.execute(
                """
                SELECT * FROM loyalty_giveaway_entries
                WHERE giveaway_id = $1 AND is_shadow_banned = FALSE
                """,
                [giveaway_id],
            )

            if not entries:
                return []

            # Build weighted pool
            weighted_pool = []
            for entry in entries:
                weight = float(entry['weight_multiplier']) * entry['entry_count']
                weighted_pool.extend([entry] * int(weight * 100))

            if not weighted_pool:
                return []

            # Draw winners without replacement
            winners = []
            drawn_user_ids = set()

            for winner_num in range(1, num_winners + 1):
                # Filter out already-drawn users
                available = [e for e in weighted_pool
                             if e['platform_user_id'] not in drawn_user_ids]
                if not available:
                    break

                winner = random.choice(available)
                drawn_user_ids.add(winner['platform_user_id'])

                # Record winner
                await self.dal.execute(
                    """
                    INSERT INTO loyalty_giveaway_winners
                        (giveaway_id, winner_number, user_id, platform)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (giveaway_id, winner_number) DO NOTHING
                    """,
                    [giveaway_id, winner_num,
                     winner['platform_user_id'], winner['platform']],
                )

                # Assign key if this is a key giveaway
                key_info = None
                if giveaway.get('giveaway_type') == 'game_key':
                    key_info = await self._assign_key_to_winner(
                        giveaway_id, winner_num,
                    )

                winners.append({
                    'winner_number': winner_num,
                    'platform': winner['platform'],
                    'platform_user_id': winner['platform_user_id'],
                    'platform_username': winner.get('platform_username'),
                    'key_assigned': key_info is not None,
                })

            # Update giveaway status
            await self.dal.execute(
                """
                UPDATE loyalty_giveaways
                SET status = 'completed', updated_at = NOW()
                WHERE id = $1
                """,
                [giveaway_id],
            )

            logger.info(
                "Giveaway %s: drew %d winners", giveaway_id, len(winners),
            )
            return winners

        except Exception as e:
            logger.error(f"Error drawing winners: {e}")
            return []

    async def _assign_key_to_winner(
        self,
        giveaway_id: int,
        winner_number: int,
    ) -> Optional[Dict[str, Any]]:
        """Claim next unclaimed key and assign to a winner slot."""
        try:
            # Atomically claim the next available key
            key_rows = await self.dal.execute(
                """
                UPDATE loyalty_giveaway_keys
                SET is_claimed = TRUE, claimed_at = NOW()
                WHERE id = (
                    SELECT id FROM loyalty_giveaway_keys
                    WHERE giveaway_id = $1 AND is_claimed = FALSE AND is_valid = TRUE
                    ORDER BY id
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id, key_value, key_platform
                """,
                [giveaway_id],
            )

            if not key_rows:
                logger.warning("No unclaimed keys for giveaway %s", giveaway_id)
                return None

            key = key_rows[0]

            # Link key to winner
            await self.dal.execute(
                """
                UPDATE loyalty_giveaway_winners
                SET key_id = $1
                WHERE giveaway_id = $2 AND winner_number = $3
                """,
                [key['id'], giveaway_id, winner_number],
            )

            return {
                'key_id': key['id'],
                'key_platform': key['key_platform'],
            }

        except Exception as e:
            logger.error(f"Error assigning key to winner: {e}")
            return None

    async def get_winners(
        self,
        giveaway_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all winners for a giveaway."""
        try:
            rows = await self.dal.execute(
                """
                SELECT w.winner_number, w.user_id, w.platform,
                       w.notified, w.notified_at, w.created_at,
                       k.key_platform
                FROM loyalty_giveaway_winners w
                LEFT JOIN loyalty_giveaway_keys k ON w.key_id = k.id
                WHERE w.giveaway_id = $1
                ORDER BY w.winner_number
                """,
                [giveaway_id],
            )
            return [dict(r) for r in (rows or [])]
        except Exception as e:
            logger.error(f"Error getting winners: {e}")
            return []
