"""
Quote Service

Manages community quotes with full-text search, author filtering, and pagination support.
Uses migration 015 (quotes table with PostgreSQL full-text search).
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class QuoteService:
    """
    Service for managing community quotes.

    Features:
    - Add/update/delete quotes
    - Full-text search using PostgreSQL tsvector
    - Random quote selection
    - Search by author
    - Pagination support for listing quotes
    - Soft-delete support (deleted_at column)
    """

    def __init__(self, dal):
        """
        Initialize quote service with AsyncDAL instance.

        Args:
            dal: AsyncDAL database access layer
        """
        self.dal = dal

    async def add_quote(
        self,
        community_id: int,
        text: str,
        author: Optional[str] = None,
        added_by_user_id: Optional[int] = None,
        quoted_user_id: Optional[int] = None,
        platform: Optional[str] = None,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_approved: bool = True
    ) -> Dict[str, Any]:
        """
        Add a new quote to the database.

        Args:
            community_id: Community ID
            text: The quote text
            author: Quote author name
            added_by_user_id: User ID who added the quote
            quoted_user_id: User ID being quoted (if applicable)
            platform: Platform where quote originated (e.g., 'twitch', 'discord')
            context: Additional context about the quote
            tags: List of tags for categorization
            is_approved: Whether quote is approved

        Returns:
            Dictionary with quote ID and details
        """
        try:
            sql = """
                INSERT INTO quotes
                (community_id, quote_text, quoted_user_id, quoted_username,
                 added_by_user_id, platform, context, tags, is_approved,
                 created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, updated_at
            """
            params = [
                community_id,
                text,
                quoted_user_id,
                author,
                added_by_user_id,
                platform,
                context,
                tags if tags else None,
                is_approved,
                datetime.utcnow(),
                datetime.utcnow()
            ]

            result = await self.dal.execute(sql, params)

            if result and len(result) > 0:
                row = result[0]
                quote_id = row['id']
                logger.info(
                    f"Quote {quote_id} added in community {community_id} "
                    f"by user {added_by_user_id}"
                )
                return {
                    'id': quote_id,
                    'community_id': community_id,
                    'quote_text': text,
                    'author': author,
                    'added_by_user_id': added_by_user_id,
                    'created_at': row['created_at'].isoformat() if row['created_at'] else None,
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None
                }

            raise Exception("Failed to insert quote")

        except Exception as e:
            logger.error(f"Failed to add quote: {e}")
            raise

    async def get_quote(self, quote_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific quote by ID.

        Args:
            quote_id: Quote ID to retrieve

        Returns:
            Quote dictionary or None if not found
        """
        try:
            sql = """
                SELECT id, community_id, quote_text, quoted_user_id,
                       quoted_username, added_by_user_id, platform, context,
                       tags, is_approved, created_at, updated_at, deleted_at
                FROM quotes
                WHERE id = %s AND deleted_at IS NULL
            """
            result = await self.dal.execute(sql, [quote_id])

            if result and len(result) > 0:
                return self._row_to_dict(result[0])

            return None

        except Exception as e:
            logger.error(f"Failed to get quote {quote_id}: {e}")
            raise

    async def get_random_quote(self, community_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a random quote from the community.

        Args:
            community_id: Community ID

        Returns:
            Random quote dictionary or None if no quotes exist
        """
        try:
            sql = """
                SELECT id, community_id, quote_text, quoted_user_id,
                       quoted_username, added_by_user_id, platform, context,
                       tags, is_approved, created_at, updated_at, deleted_at
                FROM quotes
                WHERE community_id = %s AND deleted_at IS NULL AND is_approved = TRUE
                ORDER BY RANDOM()
                LIMIT 1
            """
            result = await self.dal.execute(sql, [community_id])

            if result and len(result) > 0:
                return self._row_to_dict(result[0])

            logger.info(f"No approved quotes found for community {community_id}")
            return None

        except Exception as e:
            logger.error(f"Failed to get random quote for community {community_id}: {e}")
            raise

    async def search_quotes(
        self,
        community_id: int,
        query: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search quotes using PostgreSQL full-text search.

        Args:
            community_id: Community ID
            query: Search query string
            limit: Maximum results per page
            offset: Pagination offset

        Returns:
            Tuple of (list of matching quotes, total count)
        """
        try:
            # Get total count
            count_sql = """
                SELECT COUNT(*)
                FROM quotes
                WHERE community_id = %s
                  AND deleted_at IS NULL
                  AND search_vector @@ plainto_tsquery('english', %s)
            """
            count_result = await self.dal.execute(count_sql, [community_id, query])
            total_count = count_result[0]['count'] if count_result else 0

            # Get paginated results with ranking
            search_sql = """
                SELECT id, community_id, quote_text, quoted_user_id,
                       quoted_username, added_by_user_id, platform, context,
                       tags, is_approved, created_at, updated_at, deleted_at
                FROM quotes
                WHERE community_id = %s
                  AND deleted_at IS NULL
                  AND search_vector @@ plainto_tsquery('english', %s)
                ORDER BY ts_rank(search_vector, plainto_tsquery('english', %s)) DESC,
                         created_at DESC
                LIMIT %s OFFSET %s
            """
            params = [community_id, query, query, limit, offset]
            results = await self.dal.execute(search_sql, params)

            quotes = [self._row_to_dict(row) for row in results]

            logger.info(
                f"Full-text search found {len(quotes)} quotes for community {community_id} "
                f"with query '{query}'"
            )
            return quotes, total_count

        except Exception as e:
            logger.error(f"Failed to search quotes in community {community_id}: {e}")
            raise

    async def get_quotes_by_author(
        self,
        community_id: int,
        author: str,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get all quotes by a specific author in a community.

        Args:
            community_id: Community ID
            author: Author name to filter by
            limit: Maximum results per page
            offset: Pagination offset

        Returns:
            Tuple of (list of quotes, total count)
        """
        try:
            # Get total count
            count_sql = """
                SELECT COUNT(*)
                FROM quotes
                WHERE community_id = %s
                  AND deleted_at IS NULL
                  AND quoted_username ILIKE %s
            """
            count_result = await self.dal.execute(
                count_sql,
                [community_id, f"%{author}%"]
            )
            total_count = count_result[0]['count'] if count_result else 0

            # Get paginated results
            search_sql = """
                SELECT id, community_id, quote_text, quoted_user_id,
                       quoted_username, added_by_user_id, platform, context,
                       tags, is_approved, created_at, updated_at, deleted_at
                FROM quotes
                WHERE community_id = %s
                  AND deleted_at IS NULL
                  AND quoted_username ILIKE %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params = [community_id, f"%{author}%", limit, offset]
            results = await self.dal.execute(search_sql, params)

            quotes = [self._row_to_dict(row) for row in results]

            logger.info(
                f"Found {len(quotes)} quotes by author '{author}' "
                f"in community {community_id}"
            )
            return quotes, total_count

        except Exception as e:
            logger.error(
                f"Failed to get quotes by author '{author}' "
                f"in community {community_id}: {e}"
            )
            raise

    async def get_quotes(
        self,
        community_id: int,
        limit: int = 50,
        offset: int = 0,
        only_approved: bool = True
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get paginated list of quotes for a community.

        Args:
            community_id: Community ID
            limit: Maximum results per page
            offset: Pagination offset
            only_approved: Filter to only approved quotes

        Returns:
            Tuple of (list of quotes, total count)
        """
        try:
            approval_filter = "AND is_approved = TRUE" if only_approved else ""

            # Get total count
            count_sql = f"""
                SELECT COUNT(*)
                FROM quotes
                WHERE community_id = %s AND deleted_at IS NULL {approval_filter}
            """
            count_result = await self.dal.execute(count_sql, [community_id])
            total_count = count_result[0]['count'] if count_result else 0

            # Get paginated results
            list_sql = f"""
                SELECT id, community_id, quote_text, quoted_user_id,
                       quoted_username, added_by_user_id, platform, context,
                       tags, is_approved, created_at, updated_at, deleted_at
                FROM quotes
                WHERE community_id = %s AND deleted_at IS NULL {approval_filter}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            params = [community_id, limit, offset]
            results = await self.dal.execute(list_sql, params)

            quotes = [self._row_to_dict(row) for row in results]

            logger.info(
                f"Retrieved {len(quotes)} quotes for community {community_id} "
                f"(limit={limit}, offset={offset})"
            )
            return quotes, total_count

        except Exception as e:
            logger.error(f"Failed to list quotes for community {community_id}: {e}")
            raise

    async def delete_quote(self, quote_id: int) -> bool:
        """
        Soft-delete a quote (sets deleted_at timestamp).

        Args:
            quote_id: Quote ID to delete

        Returns:
            True if successful, False if quote not found
        """
        try:
            sql = """
                UPDATE quotes
                SET deleted_at = %s, updated_at = %s
                WHERE id = %s AND deleted_at IS NULL
            """
            params = [datetime.utcnow(), datetime.utcnow(), quote_id]

            await self.dal.execute(sql, params)

            logger.info(f"Quote {quote_id} deleted (soft-delete)")
            return True

        except Exception as e:
            logger.error(f"Failed to delete quote {quote_id}: {e}")
            raise

    async def update_quote(
        self,
        quote_id: int,
        text: Optional[str] = None,
        author: Optional[str] = None,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_approved: Optional[bool] = None,
        platform: Optional[str] = None
    ) -> bool:
        """
        Update quote details.

        Args:
            quote_id: Quote ID to update
            text: New quote text (optional)
            author: New author name (optional)
            context: New context (optional)
            tags: New tags (optional)
            is_approved: New approval status (optional)
            platform: New platform (optional)

        Returns:
            True if update successful
        """
        try:
            # Build dynamic update clause
            updates = []
            params = []

            if text is not None:
                updates.append("quote_text = %s")
                params.append(text)

            if author is not None:
                updates.append("quoted_username = %s")
                params.append(author)

            if context is not None:
                updates.append("context = %s")
                params.append(context)

            if tags is not None:
                updates.append("tags = %s")
                params.append(tags)

            if is_approved is not None:
                updates.append("is_approved = %s")
                params.append(is_approved)

            if platform is not None:
                updates.append("platform = %s")
                params.append(platform)

            if not updates:
                logger.warning(f"No fields to update for quote {quote_id}")
                return False

            # Always update updated_at
            updates.append("updated_at = %s")
            params.append(datetime.utcnow())
            params.append(quote_id)

            sql = f"""
                UPDATE quotes
                SET {', '.join(updates)}
                WHERE id = %s AND deleted_at IS NULL
            """

            await self.dal.execute(sql, params)

            logger.info(f"Quote {quote_id} updated with {len(updates) - 1} field(s)")
            return True

        except Exception as e:
            logger.error(f"Failed to update quote {quote_id}: {e}")
            raise

    async def get_quote_count(
        self,
        community_id: int,
        only_approved: bool = False
    ) -> int:
        """
        Get total number of quotes in a community.

        Args:
            community_id: Community ID
            only_approved: Count only approved quotes

        Returns:
            Total quote count
        """
        try:
            approval_filter = "AND is_approved = TRUE" if only_approved else ""
            sql = f"""
                SELECT COUNT(*) as count
                FROM quotes
                WHERE community_id = %s AND deleted_at IS NULL {approval_filter}
            """
            result = await self.dal.execute(sql, [community_id])
            return result[0]['count'] if result else 0

        except Exception as e:
            logger.error(f"Failed to count quotes for community {community_id}: {e}")
            raise

    async def get_quote_stats(self, community_id: int) -> Dict[str, Any]:
        """
        Get statistics about quotes in a community.

        Args:
            community_id: Community ID

        Returns:
            Dictionary with quote statistics
        """
        try:
            sql = """
                SELECT
                    COUNT(*) as total_quotes,
                    COUNT(*) FILTER (WHERE is_approved = TRUE) as approved_quotes,
                    COUNT(*) FILTER (WHERE is_approved = FALSE) as pending_quotes,
                    COUNT(DISTINCT quoted_username) as unique_authors,
                    MAX(created_at) as latest_quote_date
                FROM quotes
                WHERE community_id = %s AND deleted_at IS NULL
            """
            result = await self.dal.execute(sql, [community_id])

            if result:
                row = result[0]
                return {
                    'total_quotes': row['total_quotes'] or 0,
                    'approved_quotes': row['approved_quotes'] or 0,
                    'pending_quotes': row['pending_quotes'] or 0,
                    'unique_authors': row['unique_authors'] or 0,
                    'latest_quote_date': row['latest_quote_date'].isoformat()
                    if row['latest_quote_date'] else None
                }

            return {
                'total_quotes': 0,
                'approved_quotes': 0,
                'pending_quotes': 0,
                'unique_authors': 0,
                'latest_quote_date': None
            }

        except Exception as e:
            logger.error(f"Failed to get quote stats for community {community_id}: {e}")
            raise

    def _row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert database row to dictionary with proper formatting.

        Args:
            row: Database row from execute()

        Returns:
            Formatted dictionary
        """
        return {
            'id': row['id'],
            'community_id': row['community_id'],
            'quote_text': row['quote_text'],
            'quoted_user_id': row['quoted_user_id'],
            'quoted_username': row['quoted_username'],
            'added_by_user_id': row['added_by_user_id'],
            'platform': row['platform'],
            'context': row['context'],
            'tags': row['tags'],
            'is_approved': row['is_approved'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None,
            'updated_at': row['updated_at'].isoformat() if row['updated_at'] else None,
            'deleted_at': row['deleted_at'].isoformat() if row['deleted_at'] else None
        }
