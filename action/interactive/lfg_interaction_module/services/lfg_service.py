"""LFG (Looking for Group) service for managing group-finding posts."""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class LfgService:
    """Service for creating, joining, and managing LFG posts."""

    def __init__(self, dal, config):
        self.dal = dal
        self.config = config

    async def create_post(
        self,
        community_id,
        user_id,
        platform,
        game,
        activity=None,
        role=None,
        rank_or_level=None,
        player_count_needed=1,
        message=None,
        platform_message_id=None,
    ):
        """Create a new LFG post.

        Returns a success dict with post data or an error dict if the
        user has too many active posts.
        """
        try:
            # Check active post count for user
            count_rows = self.dal.executesql(
                "SELECT COUNT(*) FROM lfg_posts "
                "WHERE community_id=$1 AND user_id=$2 AND status='open'",
                placeholders=[community_id, user_id],
            )
            active_count = count_rows[0][0] if count_rows else 0

            if active_count >= self.config.LFG_MAX_ACTIVE_POSTS_PER_USER:
                return {
                    'success': False,
                    'error': (
                        f'Maximum active posts reached '
                        f'({self.config.LFG_MAX_ACTIVE_POSTS_PER_USER})'
                    ),
                }

            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.LFG_DEFAULT_EXPIRY_MINUTES
            )

            rows = self.dal.executesql(
                "INSERT INTO lfg_posts "
                "(community_id, user_id, platform, game, activity, role, "
                "rank_or_level, player_count_needed, message, "
                "platform_message_id, status, expires_at, created_at) "
                "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, "
                "'open', $11, NOW()) "
                "RETURNING id, game, activity, status, expires_at",
                placeholders=[
                    community_id,
                    user_id,
                    platform,
                    game,
                    activity,
                    role,
                    rank_or_level,
                    player_count_needed,
                    message,
                    platform_message_id,
                    expires_at,
                ],
            )

            if rows:
                row = rows[0]
                return {
                    'success': True,
                    'post': {
                        'id': row[0],
                        'game': row[1],
                        'activity': row[2],
                        'status': row[3],
                        'expires_at': row[4].isoformat()
                        if hasattr(row[4], 'isoformat')
                        else str(row[4]),
                    },
                }

            return {'success': False, 'error': 'Failed to create post'}

        except Exception as e:
            logger.error("Failed to create LFG post: %s", e)
            return {'success': False, 'error': str(e)}

    async def join_post(
        self, post_id, user_id, platform, display_name=None
    ):
        """Join an existing LFG post.

        Returns a success dict or an error if the post is not open.
        """
        try:
            # Verify post exists and is open
            post_rows = self.dal.executesql(
                "SELECT status, player_count_needed FROM lfg_posts "
                "WHERE id=$1",
                placeholders=[post_id],
            )

            if not post_rows:
                return {'success': False, 'error': 'Post not found'}

            status = post_rows[0][0]
            player_count_needed = post_rows[0][1]

            if status != 'open':
                return {
                    'success': False,
                    'error': f'Post is not open (status: {status})',
                }

            # Insert join record, ignore duplicates
            self.dal.executesql(
                "INSERT INTO lfg_joins "
                "(post_id, user_id, platform, display_name, joined_at) "
                "VALUES ($1, $2, $3, $4, NOW()) "
                "ON CONFLICT DO NOTHING",
                placeholders=[post_id, user_id, platform, display_name],
            )

            # Check if post is now filled
            count_rows = self.dal.executesql(
                "SELECT COUNT(*) FROM lfg_joins WHERE post_id=$1",
                placeholders=[post_id],
            )
            join_count = count_rows[0][0] if count_rows else 0

            if join_count >= player_count_needed:
                self.dal.executesql(
                    "UPDATE lfg_posts SET status='filled' WHERE id=$1",
                    placeholders=[post_id],
                )

            return {
                'success': True,
                'join_count': join_count,
                'filled': join_count >= player_count_needed,
            }

        except Exception as e:
            logger.error("Failed to join LFG post: %s", e)
            return {'success': False, 'error': str(e)}

    async def leave_post(self, post_id, user_id):
        """Leave an LFG post.

        If the post was filled, reverts its status back to open.
        """
        try:
            # Check current status before deleting
            status_rows = self.dal.executesql(
                "SELECT status FROM lfg_posts WHERE id=$1",
                placeholders=[post_id],
            )

            if not status_rows:
                return {'success': False, 'error': 'Post not found'}

            was_filled = status_rows[0][0] == 'filled'

            self.dal.executesql(
                "DELETE FROM lfg_joins "
                "WHERE post_id=$1 AND user_id=$2",
                placeholders=[post_id, user_id],
            )

            # If post was filled, revert to open
            if was_filled:
                self.dal.executesql(
                    "UPDATE lfg_posts SET status='open' WHERE id=$1",
                    placeholders=[post_id],
                )

            return {'success': True}

        except Exception as e:
            logger.error("Failed to leave LFG post: %s", e)
            return {'success': False, 'error': str(e)}

    async def cancel_post(self, post_id, user_id):
        """Cancel an LFG post. Only the creator can cancel."""
        try:
            rows = self.dal.executesql(
                "UPDATE lfg_posts SET status='cancelled' "
                "WHERE id=$1 AND user_id=$2 AND status IN ('open', 'filled') "
                "RETURNING id",
                placeholders=[post_id, user_id],
            )

            if rows:
                return {'success': True, 'post_id': rows[0][0]}

            return {
                'success': False,
                'error': 'Post not found or not owned by user',
            }

        except Exception as e:
            logger.error("Failed to cancel LFG post: %s", e)
            return {'success': False, 'error': str(e)}

    async def get_active_posts(self, community_id, game=None):
        """Get active LFG posts for a community.

        Optionally filter by game name.
        """
        try:
            if game:
                rows = self.dal.executesql(
                    "SELECT id, user_id, platform, game, activity, role, "
                    "rank_or_level, player_count_needed, message, status, "
                    "expires_at, created_at "
                    "FROM lfg_posts "
                    "WHERE community_id=$1 AND status='open' "
                    "AND expires_at > NOW() AND game ILIKE $2 "
                    "ORDER BY created_at DESC",
                    placeholders=[community_id, f'%{game}%'],
                )
            else:
                rows = self.dal.executesql(
                    "SELECT id, user_id, platform, game, activity, role, "
                    "rank_or_level, player_count_needed, message, status, "
                    "expires_at, created_at "
                    "FROM lfg_posts "
                    "WHERE community_id=$1 AND status='open' "
                    "AND expires_at > NOW() "
                    "ORDER BY created_at DESC",
                    placeholders=[community_id],
                )

            posts = []
            for row in rows or []:
                post_id = row[0]

                # Get join count for each post
                count_rows = self.dal.executesql(
                    "SELECT COUNT(*) FROM lfg_joins WHERE post_id=$1",
                    placeholders=[post_id],
                )
                join_count = count_rows[0][0] if count_rows else 0

                posts.append({
                    'id': post_id,
                    'user_id': row[1],
                    'platform': row[2],
                    'game': row[3],
                    'activity': row[4],
                    'role': row[5],
                    'rank_or_level': row[6],
                    'player_count_needed': row[7],
                    'message': row[8],
                    'status': row[9],
                    'expires_at': row[10].isoformat()
                    if hasattr(row[10], 'isoformat')
                    else str(row[10]),
                    'created_at': row[11].isoformat()
                    if hasattr(row[11], 'isoformat')
                    else str(row[11]),
                    'join_count': join_count,
                })

            return posts

        except Exception as e:
            logger.error("Failed to get active LFG posts: %s", e)
            return []

    async def expire_old_posts(self):
        """Expire posts that have passed their expiry time.

        Returns the count of expired posts.
        """
        try:
            rows = self.dal.executesql(
                "UPDATE lfg_posts SET status='expired' "
                "WHERE status='open' AND expires_at <= NOW() "
                "RETURNING id",
            )

            expired_count = len(rows) if rows else 0
            if expired_count > 0:
                logger.info("Expired %d LFG posts", expired_count)

            return expired_count

        except Exception as e:
            logger.error("Failed to expire LFG posts: %s", e)
            return 0
