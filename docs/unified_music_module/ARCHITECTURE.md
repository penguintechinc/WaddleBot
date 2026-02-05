# Unified Music Module Architecture

**Module**: `unified_music_module`
**Version**: 1.0.0

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Diagram](#component-diagram)
4. [Provider Architecture](#provider-architecture)
5. [Queue System](#queue-system)
6. [Playback Orchestration](#playback-orchestration)
7. [Radio Player Architecture](#radio-player-architecture)
8. [Mode Controller](#mode-controller)
9. [Data Flow](#data-flow)
10. [Database Schema](#database-schema)
11. [Scalability & Performance](#scalability--performance)

---

## Overview

The Unified Music Module is a microservice-based music playback orchestration system that provides a unified API for managing music from multiple streaming providers (Spotify, YouTube, SoundCloud) with queue-based playback and radio streaming capabilities.

### Core Design Principles

- **Provider Abstraction**: Common interface for all music providers
- **Async-First**: All operations are asynchronous for high performance
- **Community Isolation**: Separate queues and playback state per community
- **Fault Tolerance**: Graceful degradation when providers are unavailable
- **Real-time Updates**: WebSocket/HTTP integration with browser source overlay

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Applications                        │
│         (Discord Bot, Web UI, Mobile Apps)                      │
└───────────────┬─────────────────────────────────────────────────┘
                │ HTTP/REST API
                ▼
┌───────────────────────────────────────────────────────────────────┐
│                   Unified Music Module (FastAPI)                  │
├───────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Mode Controller │  │ Music Player │  │  Radio Player    │   │
│  └────────┬────────┘  └──────┬───────┘  └────────┬─────────┘   │
│           │                   │                    │              │
│           └───────────────────┴────────────────────┘              │
│                               │                                   │
│  ┌────────────────────────────┴────────────────────────────┐    │
│  │              Unified Queue Service                       │    │
│  │           (Redis-backed persistence)                     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                    │
│  ┌─────────────┬─────────────┬──────────────┬─────────────┐    │
│  │   Spotify   │   YouTube   │  SoundCloud  │    Radio    │    │
│  │   Provider  │   Provider  │   Provider   │  Providers  │    │
│  └─────────────┴─────────────┴──────────────┴─────────────┘    │
└────────┬────────────────────────────────────────────┬────────────┘
         │                                             │
         ▼                                             ▼
┌─────────────────┐                          ┌──────────────────┐
│  External APIs  │                          │  Browser Source  │
│  - Spotify API  │                          │     Overlay      │
│  - YouTube API  │                          │   (WebSocket)    │
│  - SoundCloud   │                          └──────────────────┘
│  - Radio APIs   │
└─────────────────┘

         ▼
┌─────────────────┐
│  Redis Queue    │
│  Persistence    │
└─────────────────┘

         ▼
┌─────────────────┐
│   PostgreSQL    │
│  (Radio Config) │
└─────────────────┘
```

---

## Component Diagram

### Layer Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Presentation Layer                     │
│              (API Routes & Controllers)                  │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────────┐
│                   Orchestration Layer                    │
│    ┌──────────────┐  ┌─────────────┐  ┌──────────────┐ │
│    │ Music Player │  │ Radio Player│  │     Mode     │ │
│    │  Service     │  │   Service   │  │  Controller  │ │
│    └──────────────┘  └─────────────┘  └──────────────┘ │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────────┐
│                    Business Logic Layer                  │
│         ┌──────────────────────────────┐                 │
│         │   Unified Queue Service      │                 │
│         │  (Vote-based prioritization) │                 │
│         └──────────────────────────────┘                 │
└───────────────────────┬──────────────────────────────────┘
                        │
┌───────────────────────┴──────────────────────────────────┐
│                   Data Access Layer                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │
│  │   Redis    │  │ PostgreSQL │  │  Provider APIs   │  │
│  │ (Queues)   │  │  (Config)  │  │ (Music Services) │  │
│  └────────────┘  └────────────┘  └──────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## Provider Architecture

### Base Provider Interface

All music providers implement the `BaseMusicProvider` abstract class:

```python
class BaseMusicProvider(ABC):
    """Abstract base class for music providers."""

    PROVIDER_NAME: str = NotImplemented

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[MusicTrack]:
        """Search for tracks."""
        pass

    @abstractmethod
    async def get_track(self, track_id: str) -> Optional[MusicTrack]:
        """Get track by ID."""
        pass

    @abstractmethod
    async def play(self, track_id: str) -> bool:
        """Start playing a track."""
        pass

    @abstractmethod
    async def pause(self) -> bool:
        """Pause playback."""
        pass

    @abstractmethod
    async def resume(self) -> bool:
        """Resume playback."""
        pass

    @abstractmethod
    async def skip(self) -> bool:
        """Skip to next track."""
        pass

    @abstractmethod
    async def get_now_playing(self) -> Optional[MusicTrack]:
        """Get current track info."""
        pass

    @abstractmethod
    async def is_authenticated(self) -> bool:
        """Check authentication status."""
        pass

    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Authenticate with provider."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health."""
        pass
```

### Provider Implementations

#### Spotify Provider

**File**: `providers/spotify_provider.py`

**Key Features**:
- OAuth2 authentication with automatic token refresh
- Playback control via Spotify Web API
- Device management
- Playlist support
- Queue management

**API Endpoints Used**:
```
POST   /api/token                   # Auth
GET    /search                      # Search
GET    /tracks/{id}                 # Track info
GET    /me/player                   # Playback state
PUT    /me/player/play              # Play/resume
PUT    /me/player/pause             # Pause
POST   /me/player/next              # Skip
POST   /me/player/queue             # Add to queue
GET    /me/player/devices           # List devices
```

**Authentication Flow**:
```
1. get_auth_url() → Authorization URL
2. User authorizes → Authorization code
3. exchange_code() → Access token + Refresh token
4. Auto-refresh when token expires (5min before expiry)
5. Retry with new token on 401 responses
```

---

#### YouTube Provider

**File**: `providers/youtube_provider.py`

**Key Features**:
- API key authentication
- YouTube Data API v3 integration
- Video search with metadata
- Browser-source playback (iframe)
- Duration parsing (ISO 8601)

**API Endpoints Used**:
```
GET    /search                      # Search videos
GET    /videos                      # Video details
```

**URL Parsing**:
```python
# Supports:
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://youtu.be/dQw4w9WgXcQ
```

**Playback Model**:
- State managed internally (no direct playback control)
- Browser source handles actual playback via iframe
- Metadata fetched from API

---

#### SoundCloud Provider

**File**: `providers/soundcloud_provider.py`

**Key Features**:
- OAuth2 authentication
- Track search and metadata
- Stream URL generation
- Internal queue management
- Non-expiring tokens support

**API Endpoints Used**:
```
POST   /oauth/token                 # Auth
GET    /tracks                      # Search
GET    /tracks/{id}                 # Track info
GET    /tracks/{id}/stream          # Stream URL
GET    /me                          # User profile
GET    /users/{id}/likes            # User likes
GET    /playlists/{id}              # Playlist tracks
```

**Authentication Flow**:
```
1. get_auth_url() → Authorization URL
2. exchange_code() → Access token (potentially non-expiring)
3. Optional refresh token for rotating tokens
```

---

### MusicTrack Data Model

```python
@dataclass
class MusicTrack:
    track_id: str              # Provider-specific ID
    name: str                  # Track title
    artist: str                # Artist name(s)
    album: str                 # Album name
    album_art_url: str         # Album artwork URL
    duration_ms: int           # Duration in milliseconds
    provider: str              # Provider name
    uri: str                   # Provider-specific URI
    metadata: Dict[str, Any]   # Additional metadata
```

**Provider-Specific Metadata**:

| Provider | Metadata Fields |
|----------|----------------|
| Spotify | `popularity`, `explicit`, `external_urls` |
| YouTube | `description`, `published_at`, `channel_id`, `tags` |
| SoundCloud | `url`, `stream_url`, `playback_count`, `likes_count`, `genre` |

---

## Queue System

### UnifiedQueue Architecture

**File**: `services/unified_queue.py`

**Storage**: Redis-backed with in-memory fallback

**Key Components**:

```
┌────────────────────────────────────────────┐
│         UnifiedQueue Service               │
├────────────────────────────────────────────┤
│  ┌──────────────────────────────────────┐ │
│  │      Queue Operations                │ │
│  │  - add_track()                       │ │
│  │  - remove_track()                    │ │
│  │  - vote_track()                      │ │
│  │  - get_next_track()                  │ │
│  │  - clear_queue()                     │ │
│  │  - reorder_by_votes()                │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │      Status Management               │ │
│  │  - mark_playing()                    │ │
│  │  - mark_played()                     │ │
│  │  - skip_current()                    │ │
│  └──────────────────────────────────────┘ │
│                                            │
│  ┌──────────────────────────────────────┐ │
│  │      History & Stats                 │ │
│  │  - get_history()                     │ │
│  │  - get_stats()                       │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
           │                 │
           ▼                 ▼
      ┌─────────┐      ┌──────────────┐
      │  Redis  │      │  In-Memory   │
      │ Primary │      │   Fallback   │
      └─────────┘      └──────────────┘
```

### QueueItem Data Model

```python
@dataclass
class QueueItem:
    id: str                        # UUID
    track: MusicTrack              # Track object
    requested_by_user_id: str      # User who requested
    requested_at: str              # ISO timestamp
    votes: int                     # Vote count (can be negative)
    position: int                  # Position in queue (0-indexed)
    status: QueueStatus            # queued, playing, played, skipped
    community_id: int              # Community/channel ID
    voters: List[str]              # List of user IDs who voted
```

### Queue Status Lifecycle

```
        add_track()
            │
            ▼
      ┌──────────┐
      │  QUEUED  │ ◄──┐
      └────┬─────┘    │
           │          │ vote_track()
           │          │ (reorders)
           ▼          │
     mark_playing()   │
           │          │
           ▼          │
      ┌──────────┐   │
      │ PLAYING  │   │
      └────┬─────┘   │
           │          │
     ┌─────┴─────┐   │
     │           │   │
     ▼           ▼   │
┌─────────┐ ┌──────────┐
│ PLAYED  │ │ SKIPPED  │
└─────────┘ └──────────┘
```

### Vote-Based Prioritization

```python
# Sorting algorithm
queued_items.sort(
    key=lambda x: (-x.votes, x.requested_at)
)
# Higher votes = higher priority
# Same votes = FIFO (earlier requested first)
```

**Voting Rules**:
- Users can vote once per track
- Votes can be up (+1) or down (-1)
- Duplicate votes from same user are ignored
- Queue automatically reorders after voting

### Redis Key Structure

```
{namespace}:{community_id}:queue
```

**Example**:
```
music_queue:1:queue
music_queue:42:queue
```

**Data Format** (JSON array):
```json
[
  {
    "id": "uuid",
    "track": { /* MusicTrack */ },
    "requested_by_user_id": "user123",
    "requested_at": "2025-12-16T12:34:56.789Z",
    "votes": 5,
    "position": 0,
    "status": "queued",
    "community_id": 1,
    "voters": ["user123", "user456"]
  }
]
```

---

## Playback Orchestration

### MusicPlayer Service

**File**: `services/music_player.py`

**Responsibilities**:
- Orchestrate playback across providers
- Manage playback state per community
- Process queue items
- Send browser source updates

**Architecture**:

```
┌───────────────────────────────────────────────┐
│           MusicPlayer Service                 │
├───────────────────────────────────────────────┤
│                                               │
│  Providers: Dict[str, BaseMusicProvider]     │
│    ├─ "spotify": SpotifyProvider             │
│    ├─ "youtube": YouTubeProvider             │
│    └─ "soundcloud": SoundCloudProvider       │
│                                               │
│  Queue: UnifiedQueue                          │
│                                               │
│  Playback States: Dict[int, PlaybackState]   │
│    └─ {community_id: state}                  │
│                                               │
└───────────────────────────────────────────────┘
```

### PlaybackState Model

```python
@dataclass
class PlaybackState:
    community_id: int
    current_queue_item: Optional[QueueItem]
    is_playing: bool
    is_paused: bool
    current_provider: Optional[str]
    started_at: Optional[str]
    last_updated: Optional[str]
```

### Play Flow

```
play(community_id)
    │
    ├─→ Get next track from queue
    │   queue.get_next_track(community_id)
    │
    ├─→ Mark as playing in queue
    │   queue.mark_playing(item.id, community_id)
    │
    ├─→ Select provider
    │   provider = providers[track.provider]
    │
    ├─→ Start playback
    │   provider.play(track.track_id)
    │
    ├─→ Update playback state
    │   playback_states[community_id] = new_state
    │
    └─→ Send browser source update
        POST {browser_source_url}/api/v1/internal/now-playing
```

### Browser Source Integration

**Update Payload**:
```json
{
  "community_id": 1,
  "type": "now_playing",
  "timestamp": "2025-12-16T12:34:56.789Z",
  "track": {
    "name": "Song Title",
    "artist": "Artist Name",
    "album": "Album Name",
    "album_art_url": "https://...",
    "duration_ms": 213000,
    "provider": "spotify"
  }
}
```

---

## Radio Player Architecture

### RadioPlayer Service

**File**: `services/radio_player.py`

**Responsibilities**:
- Manage single-stream radio playback per community
- Fetch metadata from radio APIs
- Store station configurations in PostgreSQL
- Send overlay updates

**Architecture**:

```
┌─────────────────────────────────────────────┐
│          RadioPlayer Service                │
├─────────────────────────────────────────────┤
│                                             │
│  Active Stations:                           │
│    Dict[int, (StationConfig, NowPlaying)]  │
│                                             │
│  Metadata Providers:                        │
│    ├─ IcecastMetadataFetcher               │
│    ├─ PretzelMetadataProvider              │
│    ├─ EpidemicMetadataProvider             │
│    ├─ MonstercatMetadataProvider           │
│    └─ StreamBeatsMetadataProvider          │
│                                             │
│  Metadata Tasks: Dict[int, asyncio.Task]   │
│    └─ Background refresh loops             │
│                                             │
└─────────────────────────────────────────────┘
```

### StationConfig Model

```python
@dataclass
class StationConfig:
    provider: str                  # icecast, pretzel, epidemic, etc.
    name: str                      # Station display name
    stream_url: str                # Stream URL
    api_endpoint: Optional[str]    # API endpoint for metadata
    api_key: Optional[str]         # API authentication
    metadata_path: Optional[str]   # Path/ID for metadata
    bitrate: Optional[int]         # Stream bitrate (kbps)
    codec: Optional[str]           # Audio codec (mp3, aac, etc.)
    custom_headers: Dict[str, str] # Custom HTTP headers
```

### NowPlayingInfo Model

```python
@dataclass
class NowPlayingInfo:
    title: Optional[str]           # Track title
    artist: Optional[str]          # Artist name
    album: Optional[str]           # Album name
    duration_seconds: Optional[int] # Track duration
    bitrate: Optional[int]         # Stream bitrate
    codec: Optional[str]           # Audio codec
    genre: Optional[str]           # Music genre
    thumbnail_url: Optional[str]   # Artwork URL
    updated_at: Optional[str]      # Last update timestamp
```

### Metadata Fetching

Each provider has a custom metadata fetcher:

**Icecast** (stream metadata):
```python
# Read ICY-MetaInt header
# Extract StreamTitle from metadata blocks
# Parse "Artist - Title" format
```

**Pretzel/Epidemic/Monstercat/StreamBeats** (API):
```python
# Poll provider API every 30 seconds
# Extract track info from JSON response
# Cache with TTL
```

### Metadata Refresh Loop

```python
async def _refresh_metadata_loop(community_id, provider):
    while True:
        await asyncio.sleep(30)  # 30-second intervals
        metadata = await provider.fetch_now_playing()
        if metadata:
            update_cache(community_id, metadata)
            update_active_station(community_id, metadata)
```

---

## Mode Controller

### ModeController Service

**File**: `services/mode_controller.py`

**Responsibilities**:
- Switch between music and radio modes
- Ensure mutual exclusivity (only 1 mode active per community)
- Preserve state during mode transitions
- Send mode change notifications

**Architecture**:

```
┌──────────────────────────────────────────┐
│       ModeController Service             │
├──────────────────────────────────────────┤
│                                          │
│  Music Player: MusicPlayer               │
│  Radio Player: RadioPlayer               │
│                                          │
│  Mode States: Dict[int, ModeState]       │
│    └─ {community_id: state}             │
│                                          │
│  Transition Locks: Dict[int, Lock]       │
│    └─ Prevent concurrent mode switches  │
│                                          │
└──────────────────────────────────────────┘
```

### ModeState Model

```python
@dataclass
class ModeState:
    community_id: int
    active_mode: PlayMode              # music, radio, none
    previous_mode: Optional[PlayMode]
    music_paused_on_switch: bool       # Was music paused when switching?
    radio_paused_on_switch: bool       # Was radio paused when switching?
    switched_at: Optional[str]
    last_updated: Optional[str]
```

### Mode Transition Flow

```
switch_to_radio(community_id)
    │
    ├─→ Acquire transition lock
    │   async with locks[community_id]:
    │
    ├─→ Check current mode
    │   if mode == RADIO: return True
    │
    ├─→ Pause music if playing
    │   if mode == MUSIC:
    │       music_player.pause(community_id)
    │       mode_state.music_paused_on_switch = True
    │
    ├─→ Update mode state
    │   mode_state.active_mode = RADIO
    │   mode_state.switched_at = now()
    │
    └─→ Send notification
        POST {browser_source_url}/api/v1/internal/mode-change
```

---

## Data Flow

### Request to Playback Flow

```
1. Client Request
   ↓
2. API Endpoint (FastAPI route)
   ↓
3. Controller (parse & validate)
   ↓
4. MusicPlayer.play(community_id)
   ↓
5. UnifiedQueue.get_next_track(community_id)
   ↓
6. Redis fetch queue data
   ↓
7. UnifiedQueue.mark_playing(item_id)
   ↓
8. Select provider based on track.provider
   ↓
9. Provider.play(track_id)
   ↓
10. External API call (Spotify/YouTube/SoundCloud)
   ↓
11. Update PlaybackState
   ↓
12. Send browser source update (async task)
   ↓
13. Return success response to client
```

### Queue Addition Flow

```
1. Client adds track
   ↓
2. POST /api/v1/queue/{community_id}/add
   ↓
3. Parse track URL/ID
   ↓
4. Provider.get_track(track_id)
   ↓
5. External API fetch track metadata
   ↓
6. Create MusicTrack object
   ↓
7. UnifiedQueue.add_track(track, user_id, community_id)
   ↓
8. Get current queue to determine position
   ↓
9. Create QueueItem with position
   ↓
10. Store in Redis
   ↓
11. Return queue position to client
```

---

## Database Schema

### PostgreSQL Tables

#### music_provider_config

Stores radio station configurations per community.

```sql
CREATE TABLE music_provider_config (
    id SERIAL PRIMARY KEY,
    community_id INTEGER NOT NULL,
    provider_type VARCHAR(50) NOT NULL,  -- 'icecast', 'pretzel', etc.
    config JSONB NOT NULL,               -- Station configuration
    is_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(community_id, provider_type)
);
```

**Config JSONB Structure**:
```json
{
  "name": "Station Name",
  "stream_url": "https://...",
  "api_endpoint": "https://...",
  "api_key": "...",
  "metadata_path": "...",
  "bitrate": 128,
  "codec": "mp3",
  "custom_headers": {}
}
```

#### music_radio_state

Tracks active radio stations per community.

```sql
CREATE TABLE music_radio_state (
    community_id INTEGER PRIMARY KEY,
    mode VARCHAR(20) NOT NULL,              -- 'music' or 'radio'
    current_station_name VARCHAR(255),
    current_station_url TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Scalability & Performance

### Horizontal Scaling

**Stateless Design**:
- All state stored in Redis/PostgreSQL
- No local state (except caches)
- Multiple instances can run in parallel

**Load Balancing**:
```
┌─────────┐
│  nginx  │
└────┬────┘
     │
     ├──→ [Music Module Instance 1]
     ├──→ [Music Module Instance 2]
     └──→ [Music Module Instance 3]
              │
              ▼
         [Shared Redis]
```

### Performance Characteristics

| Operation | Latency | Throughput |
|-----------|---------|------------|
| Queue add | ~10ms | 1000 req/s |
| Queue fetch | ~5ms | 2000 req/s |
| Playback start | ~100-500ms | 100 req/s |
| Provider search | ~200-1000ms | 50 req/s |

### Caching Strategy

**Queue Cache**: Redis with 24-hour TTL
**Metadata Cache**: In-memory with 30-second TTL
**Provider Tokens**: In-memory with auto-refresh

### Resource Usage

**Per Instance**:
- Memory: ~200MB base + ~50MB per 1000 active communities
- CPU: ~5% idle, ~20% under load
- Connections: ~100 HTTP (providers), 1 Redis, 1 PostgreSQL

**Redis Storage**:
- ~5KB per queue item
- ~50KB per community with 10-item queue

---

**Last Updated**: 2025-12-16
**Architecture Version**: 1.0.0
**Maintainer**: Waddles Development Team
