# Unified Music Module Usage Guide

**Module**: `unified_music_module`
**Version**: 1.0.0

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Chat Commands](#chat-commands)
3. [Web UI Features](#web-ui-features)
4. [Python SDK Usage](#python-sdk-usage)
5. [Provider-Specific Features](#provider-specific-features)
6. [Queue Management](#queue-management)
7. [Radio Streaming](#radio-streaming)
8. [Mode Switching](#mode-switching)
9. [Advanced Usage](#advanced-usage)
10. [Best Practices](#best-practices)

---

## Quick Start

### Basic Music Playback

```bash
# 1. Add a track to queue
curl -X POST http://localhost:8051/api/v1/queue/1/add \
  -H "Content-Type: application/json" \
  -d '{
    "track_url": "spotify:track:4cOdK2GP6pPG3x0fA5CkPo",
    "requested_by_user_id": "user123",
    "provider": "spotify"
  }'

# 2. Start playback
curl -X POST http://localhost:8051/api/v1/playback/1/play

# 3. Check what's playing
curl http://localhost:8051/api/v1/playback/1/now-playing
```

### Quick Radio Playback

```bash
# 1. Start radio station
curl -X POST http://localhost:8051/api/v1/radio/1/play \
  -H "Content-Type: application/json" \
  -d '{"station_name": "pretzel_lofi"}'

# 2. Check current station
curl http://localhost:8051/api/v1/radio/1/now-playing
```

---

## Chat Commands

### Discord Bot Integration

The music module integrates with Discord through chat commands:

| Command | Syntax | Description | Example |
|---------|--------|-------------|---------|
| `!play` | `!play <query or URL>` | Search and add track to queue | `!play never gonna give you up` |
| `!skip` | `!skip` | Skip current track | `!skip` |
| `!pause` | `!pause` | Pause playback | `!pause` |
| `!resume` | `!resume` | Resume playback | `!resume` |
| `!queue` | `!queue [page]` | Show current queue | `!queue` or `!queue 2` |
| `!nowplaying` | `!nowplaying` or `!np` | Show current track | `!np` |
| `!vote` | `!vote <position> [up\|down]` | Vote on queued track | `!vote 3 up` |
| `!remove` | `!remove <position>` | Remove track from queue | `!remove 5` |
| `!clear` | `!clear` | Clear entire queue | `!clear` |
| `!radio` | `!radio <station>` | Switch to radio mode | `!radio pretzel_lofi` |
| `!radio stop` | `!radio stop` | Stop radio playback | `!radio stop` |
| `!volume` | `!volume <0-100>` | Set volume (Spotify only) | `!volume 75` |

### Command Examples

#### Adding Tracks

```
# Search and add
User: !play never gonna give you up
Bot: 🎵 Added "Never Gonna Give You Up" by Rick Astley to queue (position 3)

# Direct URL (Spotify)
User: !play https://open.spotify.com/track/4cOdK2GP6pPG3x0fA5CkPo
Bot: 🎵 Added "Never Gonna Give You Up" by Rick Astley to queue (position 4)

# Direct URL (YouTube)
User: !play https://www.youtube.com/watch?v=dQw4w9WgXcQ
Bot: 🎵 Added "Rick Astley - Never Gonna Give You Up" to queue (position 5)
```

#### Queue Management

```
# View queue
User: !queue
Bot: 📋 Current Queue (10 tracks):
     1. 🎵 "Song A" by Artist A (5 votes) - @user1
     2. 🎵 "Song B" by Artist B (3 votes) - @user2
     3. 🎵 "Song C" by Artist C (1 vote) - @user3
     ...

# Vote on track
User: !vote 2 up
Bot: ⬆️ Voted up "Song B" by Artist B (now 4 votes, position 2)

# Remove track
User: !remove 3
Bot: 🗑️ Removed "Song C" by Artist C from queue

# Clear queue
User: !clear
Bot: 🗑️ Cleared 7 tracks from queue
```

#### Playback Control

```
# Now playing
User: !np
Bot: 🎵 Now Playing:
     "Never Gonna Give You Up" by Rick Astley
     Album: Whenever You Need Somebody
     Provider: Spotify
     Requested by: @user1
     Votes: 5

# Skip
User: !skip
Bot: ⏭️ Skipped to next track: "Mr. Blue Sky" by Electric Light Orchestra

# Pause
User: !pause
Bot: ⏸️ Paused playback

# Resume
User: !resume
Bot: ▶️ Resumed playback
```

#### Radio Commands

```
# List stations
User: !radio list
Bot: 📻 Available Radio Stations:
     1. pretzel_lofi - Pretzel Lofi Hip Hop
     2. epidemic_chill - Epidemic Sound Chill
     3. monstercat - Monstercat FM

# Start radio
User: !radio pretzel_lofi
Bot: 📻 Now playing: Pretzel Lofi Hip Hop
     🎵 Current track: "Midnight Vibes" by Lofi Beats

# Stop radio
User: !radio stop
Bot: 📻 Stopped radio playback
```

---

## Web UI Features

### Queue View

The web UI provides a visual queue manager with:

- **Drag-and-drop reordering** (respects votes)
- **Real-time updates** via WebSocket
- **Album artwork** display
- **Vote buttons** (up/down)
- **Remove buttons** per track
- **Add track** search interface

**Screenshot**: `/docs/screenshots/queue-view.png`

### Now Playing Overlay

Browser source overlay displays:

- Album artwork (full-size)
- Track title and artist
- Progress bar
- Provider logo (Spotify/YouTube/SoundCloud)
- Vote count
- Requested by username

**OBS Integration**:
```
Browser Source URL: http://localhost:8050/overlay?community_id=1
Width: 1920px
Height: 200px
```

### Control Panel

Web-based control panel provides:

- Play/pause/skip buttons
- Volume slider (Spotify)
- Queue visualization
- Provider status indicators
- Radio station selector
- Mode toggle (music/radio)

**Access**: `http://localhost:8051/dashboard`

---

## Python SDK Usage

### Basic Playback Example

```python
import asyncio
from providers.spotify_provider import SpotifyProvider
from providers.youtube_provider import YouTubeProvider
from services.unified_queue import UnifiedQueue
from services.music_player import MusicPlayer

async def main():
    # Initialize providers
    spotify = SpotifyProvider()
    youtube = YouTubeProvider()

    # Authenticate Spotify
    await spotify.authenticate({
        "access_token": "your_token",
        "refresh_token": "your_refresh_token"
    })

    # Create queue and player
    queue = UnifiedQueue(redis_url="redis://localhost:6379/0")
    await queue.connect()

    player = MusicPlayer(
        providers={"spotify": spotify, "youtube": youtube},
        queue=queue
    )
    await player.initialize()

    # Search for track
    results = await spotify.search("never gonna give you up", limit=1)
    track = results[0]

    # Add to queue
    community_id = 1
    queue_item = await queue.add_track(
        track=track,
        user_id="user123",
        community_id=community_id
    )

    print(f"Added: {track.name} by {track.artist} (position {queue_item.position})")

    # Start playback
    success = await player.play(community_id)
    if success:
        print("Playback started!")

    # Get now playing
    now_playing = await player.get_now_playing(community_id)
    print(f"Now playing: {now_playing['track']['name']}")

    # Cleanup
    await player.shutdown()
    await queue.disconnect()
    await spotify.close()
    await youtube.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Queue Operations

```python
# Add track with auto-search
async def add_by_search(query: str, provider, queue, community_id, user_id):
    results = await provider.search(query, limit=1)
    if results:
        track = results[0]
        item = await queue.add_track(track, user_id, community_id)
        return item
    return None

# Vote on track
async def vote_track(queue_id: str, user_id: str, upvote: bool, queue, community_id):
    new_votes = await queue.vote_track(queue_id, user_id, community_id, upvote)
    return new_votes

# Get queue with stats
async def get_queue_info(queue, community_id):
    items = await queue.get_queue(community_id)
    stats = await queue.get_stats(community_id)
    return {
        "items": items,
        "stats": stats
    }

# Clear and get history
async def clear_and_archive(queue, community_id):
    cleared = await queue.clear_queue(community_id)
    history = await queue.get_history(community_id, limit=50)
    return cleared, history
```

### Radio Player Usage

```python
from services.radio_player import RadioPlayer, StationConfig

async def radio_example():
    # Initialize radio player
    radio = RadioPlayer()
    await radio.initialize()

    # Configure Icecast station
    station = StationConfig(
        provider="icecast",
        name="My Radio",
        stream_url="https://stream.example.com/radio.mp3",
        bitrate=128,
        codec="mp3"
    )

    # Save configuration
    community_id = 1
    await radio.save_station_config(community_id, station)

    # Start playback
    success = await radio.play_station(community_id, "My Radio")
    if success:
        print("Radio started!")

    # Get now playing metadata
    now_playing = await radio.get_now_playing(community_id, use_cache=False)
    if now_playing:
        print(f"Now playing: {now_playing.title} by {now_playing.artist}")

    # Stop playback
    await radio.stop_station(community_id)

    # Cleanup
    await radio.shutdown()
```

### Mode Controller Usage

```python
from services.mode_controller import ModeController

async def mode_switching_example(music_player, radio_player):
    # Initialize mode controller
    controller = ModeController(
        music_player=music_player,
        radio_player=radio_player
    )
    await controller.initialize()

    community_id = 1

    # Switch to music mode
    success = await controller.switch_to_music(community_id)
    if success:
        print("Switched to music mode")
        # Resume music if it was paused
        await controller.resume_music_if_paused(community_id)

    # Switch to radio mode
    success = await controller.switch_to_radio(community_id)
    if success:
        print("Switched to radio mode")

    # Get current mode
    mode = await controller.get_active_mode(community_id)
    print(f"Current mode: {mode}")

    # Stop all playback
    await controller.stop_current_mode(community_id)

    # Cleanup
    await controller.shutdown()
```

---

## Provider-Specific Features

### Spotify Features

```python
# Get available devices
devices = await spotify.get_devices()
for device in devices:
    print(f"{device['name']} ({device['type']}) - Active: {device['is_active']}")

# Set active device
await spotify.set_device("device_id_here")

# Get user playlists
playlists = await spotify.get_playlists(limit=20)
for playlist in playlists:
    print(f"{playlist['name']} - {playlist['tracks']['total']} tracks")

# Get playlist tracks
tracks = await spotify.get_playlist_tracks("playlist_id", limit=50)

# Add to Spotify queue
await spotify.add_to_queue("track_id")

# Set volume
await spotify.set_volume(75)

# Seek position
await spotify.seek(60000)  # 1 minute in milliseconds

# Get full playback state
state = await spotify.get_playback_state()
```

### YouTube Features

```python
# Extract video ID from URL
video_id = youtube.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

# Search with category filter
results = await youtube.search("lofi hip hop", limit=10)

# Get detailed video info
track = await youtube.get_track("dQw4w9WgXcQ")
print(f"Duration: {track.duration_ms / 1000}s")
print(f"Channel: {track.metadata['channel_id']}")
```

### SoundCloud Features

```python
# Get user likes
likes = await soundcloud.get_user_likes(limit=50)

# Get user playlists
playlists = await soundcloud.get_user_playlists(limit=20)

# Get playlist tracks
tracks = await soundcloud.get_playlist_tracks("playlist_id", limit=100)

# Get stream URL for direct playback
stream_url = await soundcloud.get_stream_url("track_id")

# Get user profile
profile = await soundcloud.get_user_profile()
print(f"Username: {profile['username']}")
```

---

## Queue Management

### Vote-Based Prioritization

```python
# Tracks are automatically sorted by votes (highest first)
# Same votes? FIFO (first requested plays first)

# Example queue evolution:
# User1 adds Track A (0 votes, position 0)
# User2 adds Track B (0 votes, position 1)
# User3 votes Track B up (+1)
# Queue reorders: Track B (1 vote, position 0), Track A (0 votes, position 1)
```

### Queue Limits and TTL

```python
# Configure queue TTL (time-to-live)
queue = UnifiedQueue(
    redis_url="redis://localhost:6379/0",
    queue_ttl=86400  # 24 hours (default)
)

# Items older than TTL are automatically removed
# No hard limit on queue size (configurable per deployment)
```

### Queue History

```python
# Get play history
history = await queue.get_history(community_id, limit=50)

for item in history:
    print(f"{item.track.name} - Status: {item.status.value}")
    # status: 'played' or 'skipped'
```

---

## Radio Streaming

### Supported Radio Providers

| Provider | Metadata | Setup Difficulty | Cost |
|----------|----------|------------------|------|
| Icecast | Stream-based | Easy | Free |
| Pretzel | API-based | Medium | Paid |
| Epidemic Sound | API-based | Medium | Paid |
| StreamBeats | API-based | Easy | Free/Paid |
| Monstercat | API-based | Medium | Paid |

### Setting Up Icecast Station

```python
station = StationConfig(
    provider="icecast",
    name="Community Radio",
    stream_url="https://stream.example.com/radio",
    bitrate=128,
    codec="mp3"
)

await radio.save_station_config(community_id, station)
await radio.play_station(community_id, "Community Radio")
```

### Fetching Metadata

```python
# Manual metadata fetch (bypasses cache)
now_playing = await radio.get_now_playing(community_id, use_cache=False)

if now_playing:
    print(f"Title: {now_playing.title}")
    print(f"Artist: {now_playing.artist}")
    print(f"Updated: {now_playing.updated_at}")
```

---

## Mode Switching

### Music vs Radio Modes

Only **one mode** can be active per community at a time.

```python
# Switching preserves state:
# - Music pauses when switching to radio
# - Radio stops when switching to music
# - Resume music if it was paused on switch

await controller.switch_to_radio(community_id)  # Pauses music
await controller.switch_to_music(community_id)  # Stops radio
await controller.resume_music_if_paused(community_id)  # Resumes music
```

---

## Advanced Usage

### Custom Provider Implementation

```python
from providers.base_provider import BaseMusicProvider, MusicTrack

class CustomProvider(BaseMusicProvider):
    PROVIDER_NAME = "custom"

    async def search(self, query: str, limit: int = 10):
        # Implement search logic
        pass

    async def get_track(self, track_id: str):
        # Implement track fetching
        pass

    # ... implement all abstract methods
```

### Event Hooks

```python
# Custom now-playing update handler
async def on_now_playing_update(community_id, track):
    print(f"Community {community_id} now playing: {track.name}")
    # Send to custom webhook, Discord, etc.

# Integrate with MusicPlayer
player._send_now_playing_update = on_now_playing_update
```

---

## Best Practices

### Performance

1. **Use connection pooling** for HTTP clients
2. **Enable Redis caching** for queue operations
3. **Batch operations** when possible
4. **Use async/await** properly (don't block event loop)

### Error Handling

```python
try:
    await player.play(community_id)
except ProviderError as e:
    print(f"Provider error: {e}")
    # Fallback to another provider
except QueueEmpty as e:
    print(f"Queue is empty: {e}")
    # Notify user
```

### Resource Cleanup

```python
# Always cleanup resources
try:
    await player.initialize()
    # ... operations
finally:
    await player.shutdown()
    await queue.disconnect()
    await provider.close()
```

---

**Last Updated**: 2025-12-16
**Version**: 1.0.0
**Maintainer**: Waddles Development Team
