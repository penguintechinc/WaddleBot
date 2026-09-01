"""Clip management service for bookmarks, highlights, and reels."""
import logging

logger = logging.getLogger(__name__)


class ClipService:
    """Manages clip bookmarks, tags, highlights, and highlight reels."""

    def __init__(self, dal, config):
        self.dal = dal
        self.config = config

    async def bookmark_clip(
        self,
        community_id: int,
        clip_id: str,
        clip_url: str,
        title: str = None,
        game: str = None,
        tags: list = None,
        bookmarked_by: str = None,
    ) -> dict:
        """Bookmark a clip, upserting on conflict.

        Args:
            community_id: The community ID.
            clip_id: Unique clip identifier from the platform.
            clip_url: URL to the clip.
            title: Optional clip title.
            game: Optional game name.
            tags: Optional list of tags.
            bookmarked_by: Optional user who bookmarked it.

        Returns:
            Dict with the bookmarked clip data.
        """
        tags = tags or []
        result = self.dal.executesql(
            """
            INSERT INTO clip_bookmarks
                (community_id, clip_id, clip_url, title, game, tags,
                 bookmarked_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (community_id, clip_id) DO UPDATE SET
                title = EXCLUDED.title,
                game = EXCLUDED.game
            RETURNING id, community_id, clip_id, clip_url, title, game,
                      tags, bookmarked_by, is_highlight, created_at
            """,
            placeholders=[
                community_id, clip_id, clip_url, title, game, tags,
                bookmarked_by,
            ],
        )

        if result:
            row = result[0]
            return {
                "id": row[0],
                "community_id": row[1],
                "clip_id": row[2],
                "clip_url": row[3],
                "title": row[4],
                "game": row[5],
                "tags": row[6],
                "bookmarked_by": row[7],
                "is_highlight": row[8],
                "created_at": str(row[9]) if row[9] else None,
            }
        return {"error": "Failed to bookmark clip"}

    async def get_clips(
        self,
        community_id: int,
        game: str = None,
        tag: str = None,
        highlights_only: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """Retrieve clips for a community with optional filters.

        Args:
            community_id: The community ID.
            game: Optional game filter.
            tag: Optional tag filter (matches if tag is in tags array).
            highlights_only: If True, only return highlighted clips.
            limit: Maximum number of clips to return.

        Returns:
            List of clip dicts.
        """
        query = """
            SELECT id, community_id, clip_id, clip_url, title, game,
                   tags, bookmarked_by, is_highlight, created_at
            FROM clip_bookmarks
            WHERE community_id = $1
        """
        params = [community_id]
        param_idx = 2

        if game:
            query += f" AND game = ${param_idx}"
            params.append(game)
            param_idx += 1

        if tag:
            query += f" AND ${param_idx} = ANY(tags)"
            params.append(tag)
            param_idx += 1

        if highlights_only:
            query += " AND is_highlight = TRUE"

        query += f" ORDER BY created_at DESC LIMIT ${param_idx}"
        params.append(limit)

        rows = self.dal.executesql(query, placeholders=params)

        clips = []
        for row in (rows or []):
            clips.append({
                "id": row[0],
                "community_id": row[1],
                "clip_id": row[2],
                "clip_url": row[3],
                "title": row[4],
                "game": row[5],
                "tags": row[6],
                "bookmarked_by": row[7],
                "is_highlight": row[8],
                "created_at": str(row[9]) if row[9] else None,
            })
        return clips

    async def update_tags(
        self,
        community_id: int,
        clip_id: str,
        tags: list,
    ) -> dict:
        """Update tags for a bookmarked clip.

        Args:
            community_id: The community ID.
            clip_id: The clip identifier.
            tags: New list of tags.

        Returns:
            Updated clip dict or error dict.
        """
        if len(tags) > self.config.MAX_TAGS_PER_CLIP:
            return {
                "error": (
                    f"Maximum {self.config.MAX_TAGS_PER_CLIP} tags allowed"
                )
            }

        result = self.dal.executesql(
            """
            UPDATE clip_bookmarks
            SET tags = $3
            WHERE community_id = $1 AND clip_id = $2
            RETURNING id, community_id, clip_id, clip_url, title, game,
                      tags, bookmarked_by, is_highlight, created_at
            """,
            placeholders=[community_id, clip_id, tags],
        )

        if result:
            row = result[0]
            return {
                "id": row[0],
                "community_id": row[1],
                "clip_id": row[2],
                "clip_url": row[3],
                "title": row[4],
                "game": row[5],
                "tags": row[6],
                "bookmarked_by": row[7],
                "is_highlight": row[8],
                "created_at": str(row[9]) if row[9] else None,
            }
        return {"error": "Clip not found"}

    async def mark_highlight(
        self,
        community_id: int,
        clip_id: str,
        is_highlight: bool = True,
    ) -> dict:
        """Mark or unmark a clip as a highlight.

        Args:
            community_id: The community ID.
            clip_id: The clip identifier.
            is_highlight: Whether to mark as highlight.

        Returns:
            Success dict or error dict.
        """
        result = self.dal.executesql(
            """
            UPDATE clip_bookmarks
            SET is_highlight = $3
            WHERE community_id = $1 AND clip_id = $2
            RETURNING id
            """,
            placeholders=[community_id, clip_id, is_highlight],
        )

        if result:
            return {"success": True, "is_highlight": is_highlight}
        return {"error": "Clip not found"}

    async def create_reel(
        self,
        community_id: int,
        name: str,
        description: str = None,
        clip_ids: list = None,
        created_by: str = None,
    ) -> dict:
        """Create a highlight reel from a list of clip IDs.

        Args:
            community_id: The community ID.
            name: Name of the reel.
            description: Optional reel description.
            clip_ids: List of clip IDs to include.
            created_by: User who created the reel.

        Returns:
            Reel dict or error dict.
        """
        clip_ids = clip_ids or []

        if len(clip_ids) > self.config.MAX_CLIPS_PER_REEL:
            return {
                "error": (
                    f"Maximum {self.config.MAX_CLIPS_PER_REEL} clips per reel"
                )
            }

        result = self.dal.executesql(
            """
            INSERT INTO clip_highlight_reels
                (community_id, name, description, clip_ids, created_by)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING id, community_id, name, description, clip_ids,
                      created_by, is_published, created_at
            """,
            placeholders=[
                community_id, name, description, clip_ids, created_by,
            ],
        )

        if result:
            row = result[0]
            return {
                "id": row[0],
                "community_id": row[1],
                "name": row[2],
                "description": row[3],
                "clip_ids": row[4],
                "created_by": row[5],
                "is_published": row[6],
                "created_at": str(row[7]) if row[7] else None,
            }
        return {"error": "Failed to create reel"}

    async def get_reel(self, community_id: int, reel_id: int) -> dict:
        """Get a highlight reel with its embedded clips.

        Args:
            community_id: The community ID.
            reel_id: The reel ID.

        Returns:
            Reel dict with embedded clips list.
        """
        reel_rows = self.dal.executesql(
            """
            SELECT id, community_id, name, description, clip_ids,
                   created_by, is_published, created_at
            FROM clip_highlight_reels
            WHERE community_id = $1 AND id = $2
            """,
            placeholders=[community_id, reel_id],
        )

        if not reel_rows:
            return {"error": "Reel not found"}

        row = reel_rows[0]
        reel = {
            "id": row[0],
            "community_id": row[1],
            "name": row[2],
            "description": row[3],
            "clip_ids": row[4],
            "created_by": row[5],
            "is_published": row[6],
            "created_at": str(row[7]) if row[7] else None,
        }

        # Fetch the actual clips for this reel
        clip_ids = reel.get("clip_ids") or []
        clips = []
        if clip_ids:
            clip_rows = self.dal.executesql(
                """
                SELECT id, community_id, clip_id, clip_url, title, game,
                       tags, bookmarked_by, is_highlight, created_at
                FROM clip_bookmarks
                WHERE community_id = $1 AND clip_id = ANY($2)
                """,
                placeholders=[community_id, clip_ids],
            )
            for crow in (clip_rows or []):
                clips.append({
                    "id": crow[0],
                    "community_id": crow[1],
                    "clip_id": crow[2],
                    "clip_url": crow[3],
                    "title": crow[4],
                    "game": crow[5],
                    "tags": crow[6],
                    "bookmarked_by": crow[7],
                    "is_highlight": crow[8],
                    "created_at": str(crow[9]) if crow[9] else None,
                })

        reel["clips"] = clips
        return reel

    async def publish_reel(
        self,
        community_id: int,
        reel_id: int,
    ) -> dict:
        """Publish a highlight reel.

        Args:
            community_id: The community ID.
            reel_id: The reel ID.

        Returns:
            Success dict or error dict.
        """
        result = self.dal.executesql(
            """
            UPDATE clip_highlight_reels
            SET is_published = TRUE
            WHERE community_id = $1 AND id = $2
            RETURNING id
            """,
            placeholders=[community_id, reel_id],
        )

        if result:
            return {"success": True, "reel_id": reel_id, "is_published": True}
        return {"error": "Reel not found"}

    async def get_overlay_data(self, community_id: int) -> dict:
        """Get latest highlight clips for OBS browser source overlay.

        Args:
            community_id: The community ID.

        Returns:
            Dict with list of minimal clip data for overlay display.
        """
        rows = self.dal.executesql(
            """
            SELECT clip_url, title, game
            FROM clip_bookmarks
            WHERE community_id = $1 AND is_highlight = TRUE
            ORDER BY created_at DESC
            LIMIT 5
            """,
            placeholders=[community_id],
        )

        clips = []
        for row in (rows or []):
            clips.append({
                "clip_url": row[0],
                "title": row[1],
                "game": row[2],
            })

        return {"community_id": community_id, "clips": clips}
