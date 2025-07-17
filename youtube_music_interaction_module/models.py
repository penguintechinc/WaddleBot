"""
Database models for YouTube Music Interaction Module
"""

from datetime import datetime

def define_tables(db):
    """Define database tables for YouTube Music module"""
    
    # Now playing information
    db.define_table(
        'youtube_now_playing',
        db.Field('community_id', 'string', required=True, unique=True),
        db.Field('video_id', 'string', required=True),
        db.Field('title', 'string', required=True),
        db.Field('artist', 'string'),
        db.Field('album', 'string'),
        db.Field('duration', 'string'),  # Format: "3:45"
        db.Field('thumbnail_url', 'string'),
        db.Field('requested_by', 'string'),
        db.Field('started_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Search cache for quick result access
    db.define_table(
        'youtube_search_cache',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('query', 'string', required=True),
        db.Field('results', 'text'),  # JSON array of search results
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Activity logging
    db.define_table(
        'youtube_activity',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('action', 'string', required=True),
        db.Field('details', 'text'),  # JSON details
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Playlist management
    db.define_table(
        'youtube_playlists',
        db.Field('community_id', 'string', required=True),
        db.Field('playlist_name', 'string', required=True),
        db.Field('created_by', 'string', required=True),
        db.Field('is_public', 'boolean', default=True),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Playlist tracks
    db.define_table(
        'youtube_playlist_tracks',
        db.Field('playlist_id', 'reference youtube_playlists', required=True),
        db.Field('video_id', 'string', required=True),
        db.Field('title', 'string', required=True),
        db.Field('artist', 'string'),
        db.Field('duration', 'string'),
        db.Field('position', 'integer', required=True),
        db.Field('added_by', 'string', required=True),
        db.Field('added_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Queue management
    db.define_table(
        'youtube_queue',
        db.Field('community_id', 'string', required=True),
        db.Field('video_id', 'string', required=True),
        db.Field('title', 'string', required=True),
        db.Field('artist', 'string'),
        db.Field('duration', 'string'),
        db.Field('requested_by', 'string', required=True),
        db.Field('position', 'integer', required=True),
        db.Field('added_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # User preferences
    db.define_table(
        'youtube_user_preferences',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('default_volume', 'integer', default=70),
        db.Field('autoplay_enabled', 'boolean', default=True),
        db.Field('shuffle_enabled', 'boolean', default=False),
        db.Field('repeat_mode', 'string', default='none'),  # none, one, all
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # History tracking
    db.define_table(
        'youtube_history',
        db.Field('community_id', 'string', required=True),
        db.Field('video_id', 'string', required=True),
        db.Field('title', 'string', required=True),
        db.Field('artist', 'string'),
        db.Field('played_by', 'string', required=True),
        db.Field('played_at', 'datetime', default=datetime.utcnow),
        db.Field('play_count', 'integer', default=1),
        migrate=True
    )
    
    db.commit()