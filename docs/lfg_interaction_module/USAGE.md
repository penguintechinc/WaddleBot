# LFG Interaction Module - Usage Guide

## Overview

This guide demonstrates common workflows and practical use cases for the LFG Interaction Module. It covers typical scenarios from a user's perspective and provides examples for community admins, bot developers, and integrators.

## User Workflows

### Workflow 1: Creating & Finding a Raid Group

#### Scenario
Alice is a guild leader in a gaming community who needs to organize a raid. She creates an LFG post and waits for players to join.

#### Steps

1. **Alice Creates a Raid Post**
   ```bash
   curl -X POST http://localhost:8096/api/v1/lfg/posts \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $ALICE_TOKEN" \
     -d '{
       "community_id": "guild-community-uuid",
       "user_id": "alice-uuid",
       "platform": "discord",
       "game": "World of Warcraft",
       "activity": "raid",
       "role": "tank",
       "rank_or_level": "Mythic+20",
       "player_count_needed": 10,
       "message": "Mythic+ progression raid, Friday 8pm EST. Bring consumables!"
     }'
   ```

2. **Post Created Successfully**
   ```json
   {
     "status": "success",
     "data": {
       "id": "post-001",
       "status": "open",
       "current_player_count": 1,
       "player_count_needed": 10,
       "expires_at": "2026-02-24T12:30:00Z"
     }
   }
   ```

3. **Players Browse Available Posts**
   ```bash
   curl http://localhost:8096/api/v1/lfg/posts/guild-community-uuid?game=World+of+Warcraft&activity=raid \
     -H "Authorization: Bearer $TOKEN"
   ```

4. **First Player (Bob) Joins**
   ```bash
   curl -X POST http://localhost:8096/api/v1/lfg/posts/post-001/join \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $BOB_TOKEN" \
     -d '{
       "user_id": "bob-uuid",
       "platform": "discord",
       "display_name": "Bob#5678"
     }'
   ```
   Response: `current_player_count: 2` (Alice + Bob)

5. **More Players Join Progressively**
   - Player 3-9 repeat the join process
   - Each join increments `current_player_count`

6. **10th Player Joins → Group Fills Automatically**
   ```json
   {
     "status": "success",
     "data": {
       "post_id": "post-001",
       "current_player_count": 10,
       "player_count_needed": 10,
       "status": "filled",
       "joined_at": "2026-02-24T10:45:00Z"
     }
   }
   ```

7. **Post Status Transitions to "filled"**
   - System automatically transitions post to `filled`
   - List endpoints no longer show this post (unless querying `?status=filled`)
   - New players cannot join a filled post

---

### Workflow 2: Join Then Leave (Player Cancels)

#### Scenario
Bob joins a post but then realizes his schedule conflicts. He leaves to free up the slot for another player.

#### Steps

1. **Bob Joined Earlier**
   - Post had `current_player_count: 8`, `player_count_needed: 10`, `status: open`

2. **Bob Leaves**
   ```bash
   curl -X DELETE http://localhost:8096/api/v1/lfg/posts/post-001/join \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $BOB_TOKEN" \
     -d '{
       "user_id": "bob-uuid"
     }'
   ```

3. **Response Shows Reverted Status**
   ```json
   {
     "status": "success",
     "data": {
       "post_id": "post-001",
       "current_player_count": 7,
       "player_count_needed": 10,
       "status": "open",
       "left_at": "2026-02-24T10:50:00Z"
     }
   }
   ```

4. **Post Reverts to "open"**
   - System automatically transitions post back to `open`
   - Post reappears in open posts list
   - Slot available for new players

5. **New Player (Charlie) Joins**
   - Post back to `current_player_count: 8`
   - Cycle continues...

---

### Workflow 3: Creator Cancels Post

#### Scenario
Alice realizes the raid is cancelled due to low interest. She cancels the post to clean up.

#### Steps

1. **Alice Cancels the Raid**
   ```bash
   curl -X DELETE http://localhost:8096/api/v1/lfg/posts/post-001 \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $ALICE_TOKEN" \
     -d '{
       "user_id": "alice-uuid"
     }'
   ```

2. **Response Confirms Cancellation**
   ```json
   {
     "status": "success",
     "data": {
       "id": "post-001",
       "status": "cancelled",
       "cancelled_at": "2026-02-24T10:55:00Z",
       "previous_status": "open"
     }
   }
   ```

3. **All Joins Cleaned Up**
   - All participant records are removed
   - Post no longer appears in search results
   - Players notified via bot (future webhook feature)

---

### Workflow 4: Auto-Expiry of Stale Posts

#### Scenario
The system runs an hourly cron job to expire old posts that were never filled.

#### Steps

1. **Cron Job Runs Hourly**
   ```bash
   curl -X POST http://localhost:8096/api/v1/lfg/expire \
     -H "Content-Type: application/json" \
     -d '{
       "cron_token": "internal-cron-secret-token"
     }'
   ```

2. **Response Shows Expired Posts**
   ```json
   {
     "status": "success",
     "data": {
       "expired_count": 12,
       "timestamp": "2026-02-24T10:50:00Z"
     }
   }
   ```

3. **Expired Posts Cleaned Up**
   - All posts with `expires_at < now()` transitioned to `expired` status
   - Associated join records removed
   - Posts no longer appear in search results

---

## Community Admin Workflows

### Admin Workflow 1: Monitor Active Posts

#### Scenario
A community admin wants to see all active looking-for-group activity.

#### Steps

1. **Fetch All Open Posts**
   ```bash
   curl http://localhost:8096/api/v1/lfg/posts/community-uuid \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

2. **Response with Pagination**
   ```json
   {
     "status": "success",
     "data": {
       "posts": [
         {
           "id": "post-001",
           "game": "Valorant",
           "activity": "ranked",
           "current_player_count": 3,
           "player_count_needed": 5,
           "status": "open",
           "created_at": "2026-02-24T09:00:00Z",
           "expires_at": "2026-02-24T11:00:00Z"
         },
         {
           "id": "post-002",
           "game": "League of Legends",
           "activity": "casual",
           "current_player_count": 4,
           "player_count_needed": 4,
           "status": "filled",
           "created_at": "2026-02-24T08:30:00Z",
           "expires_at": "2026-02-24T10:30:00Z"
         }
       ],
       "total": 42,
       "limit": 50,
       "offset": 0
     }
   }
   ```

3. **Filter by Game**
   ```bash
   curl http://localhost:8096/api/v1/lfg/posts/community-uuid?game=Valorant \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

4. **Filter by Status**
   ```bash
   curl http://localhost:8096/api/v1/lfg/posts/community-uuid?status=filled \
     -H "Authorization: Bearer $ADMIN_TOKEN"
   ```

### Admin Workflow 2: Moderate Posts

#### Scenario
A community admin identifies an inappropriate LFG post and needs to remove it.

#### Current Capability
The system does not provide an admin-only delete endpoint. To remove inappropriate posts:
1. Contact system administrators to manually delete via database
2. Future enhancement: Add admin deletion with audit logging

---

## Integration Workflows

### Bot Integration: LFG Command

#### Scenario
Integrate LFG into bot commands (e.g., `/lfg create` in Discord).

#### Example Bot Command Handler
```python
# Pseudo-code for Discord bot integration
@bot.command(name='lfg_create')
async def create_lfg(ctx, game, activity, role, rank, players_needed, *, message):
    """
    Create an LFG post.
    Usage: /lfg_create Valorant ranked DPS Radiant 2 Looking for DPS players
    """
    payload = {
        "community_id": ctx.guild.id,
        "user_id": ctx.author.id,
        "platform": "discord",
        "game": game,
        "activity": activity,
        "role": role,
        "rank_or_level": rank,
        "player_count_needed": int(players_needed),
        "message": message
    }

    response = await http.post(
        "http://localhost:8096/api/v1/lfg/posts",
        json=payload,
        headers={"Authorization": f"Bearer {TOKEN}"}
    )

    if response.status == 201:
        post = response.json()["data"]
        embed = discord.Embed(
            title=f"{game} - {activity.upper()}",
            description=message,
            color=discord.Color.gold()
        )
        embed.add_field(name="Players Needed", value=post["player_count_needed"])
        embed.add_field(name="Current Count", value=post["current_player_count"])
        embed.add_field(name="Expires", value=post["expires_at"])
        embed.set_footer(text=f"Post ID: {post['id']}")

        await ctx.send(embed=embed)
```

### Web Dashboard Integration

#### Scenario
Display active LFG posts in a community web dashboard.

#### Example React Component
```jsx
// Pseudo-code for React dashboard
function LFGPostsList({ communityId }) {
  const [posts, setPosts] = useState([]);
  const [filter, setFilter] = useState({ game: '', activity: '' });

  useEffect(() => {
    const query = new URLSearchParams(filter).toString();
    fetch(`/api/v1/lfg/posts/${communityId}?${query}`)
      .then(r => r.json())
      .then(data => setPosts(data.data.posts));
  }, [filter]);

  return (
    <div>
      <h2>Looking for Group</h2>
      <input
        placeholder="Filter by game..."
        onChange={(e) => setFilter({...filter, game: e.target.value})}
      />
      <div className="posts-grid">
        {posts.map(post => (
          <div key={post.id} className="post-card">
            <h3>{post.game} - {post.activity}</h3>
            <p>{post.message}</p>
            <p>{post.current_player_count}/{post.player_count_needed} players</p>
            <button onClick={() => joinPost(post.id)}>Join</button>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Error Handling Examples

### Example 1: User Already Joined

```bash
curl -X POST http://localhost:8096/api/v1/lfg/posts/post-001/join \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"user_id": "user-uuid", "platform": "discord", "display_name": "User"}'
```

Response (409 Conflict):
```json
{
  "status": "error",
  "error": "ALREADY_JOINED",
  "message": "User already joined this post",
  "timestamp": "2026-02-24T10:35:00Z"
}
```

### Example 2: Max Posts Exceeded

```bash
curl -X POST http://localhost:8096/api/v1/lfg/posts \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{...}'
```

Response (409 Conflict):
```json
{
  "status": "error",
  "error": "MAX_POSTS_EXCEEDED",
  "message": "User has reached maximum active posts (3)",
  "timestamp": "2026-02-24T10:40:00Z"
}
```

### Example 3: Unauthorized Cancellation

```bash
curl -X DELETE http://localhost:8096/api/v1/lfg/posts/post-001 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $BOB_TOKEN" \
  -d '{"user_id": "bob-uuid"}'
```

Response (401 Unauthorized):
```json
{
  "status": "error",
  "error": "INSUFFICIENT_PERMISSIONS",
  "message": "Only post creator can cancel this post",
  "timestamp": "2026-02-24T10:45:00Z"
}
```

---

## Best Practices

### For Bot Developers
1. Cache game names and activity types for faster filtering
2. Implement user-friendly command aliases (e.g., `/lfg` instead of `/api/v1/lfg/posts`)
3. Handle 409 responses gracefully (max posts, already joined)
4. Set up expiry notifications before posts expire

### For Community Admins
1. Configure `LFG_DEFAULT_EXPIRY_MINUTES` based on community activity patterns
2. Monitor `MAX_ACTIVE_POSTS_PER_USER` to prevent spam
3. Encourage detailed messages to reduce irrelevant posts
4. Schedule cron expiry jobs during off-peak hours

### For Integrators
1. Implement pagination with `limit` and `offset` for large result sets
2. Cache list responses (TTL: 30-60 seconds) to reduce API load
3. Validate user_id and platform match authenticated user context
4. Retry failed requests with exponential backoff (500 errors)

---

## Rate Limiting Considerations

The module enforces per-user rate limits:
- 100 requests/minute per user
- 500 requests/minute per IP

For high-volume integrations (e.g., dashboards polling every 5 seconds), consider:
1. Increasing polling interval (e.g., 30 seconds)
2. Requesting higher rate limits from admin
3. Using server-side caching with low TTL

---

## Future Enhancements

- **Webhooks**: Real-time notifications for post creation, joins, expiry
- **Search**: Full-text search across post messages
- **Favorites**: Users can bookmark posts for quick access
- **Admin Tools**: Moderation, analytics, post deletion with audit log
- **Voice Integration**: Auto-link to voice channels when groups fill
