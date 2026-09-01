# Server Linking Guide

> How to connect platform servers/channels (Discord guilds, Slack workspaces, Twitch channels) to Waddles communities.

## Overview

A **link** is an approved relationship between a platform server/channel and a Waddles community. Links are bi-directional — either side can initiate, but both sides must confirm before the link is active.

### Link States

| State | Description |
|-------|-------------|
| `pending` | Request submitted, awaiting approval from the other side |
| `approved` | Link active — bot commands will route to this community |
| `rejected` | Request declined |

### Link Types

| Type | Description |
|------|-------------|
| `standard` | Full two-way — members can interact with all enabled modules |
| `read_only` | Bot posts announcements only; no interactive commands |
| `announcement_only` | Community announcements forwarded; no member interactions |

---

## Bi-Directional Approval Flow

### Option A: Platform owner initiates (from the bot)

1. **Discord**: Server admin runs `/join <community_name>` in any channel
   **Slack**: Workspace admin runs `/waddlebot join <community_name>`
   **Twitch**: Broadcaster types `!join <community_name>` in their stream chat

2. A `server_link_requests` row is created with `initiated_by = 'platform'`, `status = 'pending'`

3. The community admin sees the pending request in the WebUI:
   `Admin Panel → Linked Servers → Pending Requests` tab
   The request shows a "Server Initiated" badge.

4. Community admin clicks **Approve** → link becomes active; `community_servers` record created.
   Community admin clicks **Reject** → request closed.

5. The bot sends a notification DM to the platform user who ran `/join`.

### Option B: Community admin initiates (from the WebUI)

1. Community admin goes to `Admin Panel → Linked Servers` and clicks **Request Link**.

2. Fills in the form:
   - **Platform**: Discord / Slack / Twitch / YouTube / KICK
   - **Server/Channel ID**: The platform's server or channel ID (e.g., Discord guild ID)
   - **Server Name** (optional): Friendly display name
   - **Link Type**: Standard / Read Only / Announcement Only

3. A `server_link_requests` row is created with `initiated_by = 'community'`, `status = 'pending'`.

4. The platform server owner runs the approve command:
   - **Discord**: `/approve <community_name>` (server admin only)
   - **Slack**: `/waddlebot approve <community_name>` (workspace admin only)
   - **Twitch**: `!approve <community_name>` (broadcaster only)

5. The bot validates the caller has admin/broadcaster permission → link becomes active.

---

## Managing Links

### Removing a link

**From the platform:**
- Discord: `/leave <community_name>`
- Slack: `/waddlebot leave <community_name>`
- Twitch: `!leave <community_name>`

**From the WebUI:**
`Admin Panel → Linked Servers → [server row] → Remove`

### Setting a default community

If a channel is linked to multiple communities, a **default** determines which community handles commands when no per-user context override is set.

**From the platform (owner/broadcaster only):**
- `/link default <community_name>` (Discord/Slack)
- `!link default <community_name>` (Twitch)

**From the WebUI:**
`Admin Panel → Platform Settings → [server row] → Set as Default`

---

## Per-User Context Override

Individual users can override the channel default to interact with a different linked community:

```
/context switch <community_name>   # Switch to a specific community
/context reset                      # Go back to channel default
/context                            # Show current context
```

Requirements:
- The community must have an approved link to this channel
- The user must be a member of the target community

The override is stored in Redis (24h TTL) and backed by the `user_platform_context` table.

---

## Database Schema

### `server_link_requests` table

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `community_id` | integer | FK → communities |
| `platform` | varchar | `discord`, `slack`, `twitch`, `youtube`, `kick` |
| `platform_server_id` | varchar | Guild/workspace/channel ID from the platform |
| `platform_server_name` | varchar | Display name |
| `status` | varchar | `pending`, `approved`, `rejected` |
| `initiated_by` | varchar | `community` or `platform` |
| `link_type` | varchar | `standard`, `read_only`, `announcement_only` |
| `platform_channel_id` | varchar | Sub-channel ID (for Twitch/KICK which have no "servers") |
| `initiator_platform_user_id` | varchar | User who ran `/join` or similar |
| `initiator_platform_username` | varchar | Display name of initiator |

### `community_servers` table (approved links)

| Column | Type | Description |
|--------|------|-------------|
| `id` | serial | Primary key |
| `community_id` | integer | FK → communities |
| `platform` | varchar | Platform name |
| `platform_server_id` | varchar | Platform server/channel ID |
| `is_primary` | boolean | Default community for this channel? |
| `is_active` | boolean | Link is currently active |
| `status` | varchar | `approved` once link is created |

### `user_platform_context` table (per-user overrides)

| Column | Type | Description |
|--------|------|-------------|
| `platform` | varchar | Platform name |
| `platform_user_id` | varchar | User's platform ID |
| `platform_entity_id` | varchar | Channel/server ID |
| `community_id` | integer | The community the user switched to |

---

## Permissions Summary

| Action | Discord | Slack | Twitch |
|--------|---------|-------|--------|
| `/join` (initiate link) | Server Administrator | Workspace Admin | Broadcaster |
| `/approve` (confirm link) | Server Administrator | Workspace Admin | Broadcaster |
| `/leave` (remove link) | Server Administrator | Workspace Admin | Broadcaster |
| `/link default` | Server Administrator | Workspace Admin | Broadcaster |
| `/context switch` | Any user | Any user | Any user |

Non-admin users attempting admin link commands receive: "This command requires server administrator / broadcaster permission."
