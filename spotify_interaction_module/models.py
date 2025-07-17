"""
Database models for Spotify Interaction Module
"""

from datetime import datetime

def define_tables(db):
    """Define database tables for Spotify module"""
    
    # User authentication tokens
    db.define_table(
        'spotify_tokens',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('access_token', 'string', required=True),
        db.Field('refresh_token', 'string', required=True),
        db.Field('expires_at', 'datetime', required=True),
        db.Field('scope', 'string'),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Create unique index for community_id + user_id
    db.spotify_tokens._create_index('community_user_idx', 'community_id', 'user_id', unique=True)
    
    # Now playing information
    db.define_table(
        'spotify_now_playing',
        db.Field('community_id', 'string', required=True, unique=True),
        db.Field('track_uri', 'string', required=True),
        db.Field('track_name', 'string', required=True),
        db.Field('artists', 'string', required=True),
        db.Field('album', 'string'),
        db.Field('duration_ms', 'integer'),
        db.Field('album_art_url', 'string'),
        db.Field('spotify_url', 'string'),
        db.Field('preview_url', 'string'),
        db.Field('is_playing', 'boolean', default=True),
        db.Field('progress_ms', 'integer', default=0),
        db.Field('requested_by', 'string'),
        db.Field('started_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Search cache for quick result access
    db.define_table(
        'spotify_search_cache',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('query', 'string', required=True),
        db.Field('results', 'text'),  # JSON array of search results
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Activity logging
    db.define_table(
        'spotify_activity',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('action', 'string', required=True),
        db.Field('details', 'text'),  # JSON details
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # Playlist management
    db.define_table(
        'spotify_playlists',
        db.Field('community_id', 'string', required=True),
        db.Field('playlist_name', 'string', required=True),
        db.Field('created_by', 'string', required=True),
        db.Field('spotify_playlist_id', 'string'),  # Actual Spotify playlist ID
        db.Field('is_public', 'boolean', default=True),
        db.Field('is_collaborative', 'boolean', default=False),
        db.Field('created_at', 'datetime', default=datetime.utcnow),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Queue management
    db.define_table(
        'spotify_queue',
        db.Field('community_id', 'string', required=True),
        db.Field('track_uri', 'string', required=True),
        db.Field('track_name', 'string', required=True),
        db.Field('artists', 'string', required=True),
        db.Field('album', 'string'),
        db.Field('duration_ms', 'integer'),
        db.Field('requested_by', 'string', required=True),
        db.Field('position', 'integer', required=True),
        db.Field('added_at', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    # User preferences
    db.define_table(
        'spotify_user_preferences',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('auto_queue', 'boolean', default=False),
        db.Field('preferred_device', 'string'),
        db.Field('shuffle_enabled', 'boolean', default=False),
        db.Field('repeat_mode', 'string', default='off'),  # off, track, context
        db.Field('volume_percent', 'integer', default=70),
        db.Field('updated_at', 'datetime', update=datetime.utcnow),
        migrate=True
    )
    
    # Playback history
    db.define_table(
        'spotify_history',
        db.Field('community_id', 'string', required=True),
        db.Field('track_uri', 'string', required=True),
        db.Field('track_name', 'string', required=True),
        db.Field('artists', 'string', required=True),
        db.Field('played_by', 'string', required=True),
        db.Field('played_at', 'datetime', default=datetime.utcnow),
        db.Field('play_duration_ms', 'integer'),  # How long it was played
        db.Field('skipped', 'boolean', default=False),
        migrate=True
    )
    
    # Device tracking
    db.define_table(
        'spotify_devices',
        db.Field('community_id', 'string', required=True),
        db.Field('user_id', 'string', required=True),
        db.Field('device_id', 'string', required=True),
        db.Field('device_name', 'string', required=True),
        db.Field('device_type', 'string', required=True),
        db.Field('is_active', 'boolean', default=False),
        db.Field('volume_percent', 'integer'),
        db.Field('last_seen', 'datetime', default=datetime.utcnow),
        migrate=True
    )
    
    db.commit()