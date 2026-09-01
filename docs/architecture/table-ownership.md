# Table Ownership Reference

Complete inventory of all tables in WaddleBot, organized by owning module, with database accounts, access patterns, and sensitive data flags.

---

## Identity & Hub (Hub Module + Identity Core)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `hub_users` | Hub | `hub_admin` | All (column-restricted) | Identity Core | **PII, MFA** | 000 (base) |
| `hub_admins` | Hub | `hub_admin` | Hub Admin | Hub Admin | — | 000 |
| `hub_sessions` | Hub | `hub_admin` | Identity Core | Identity Core | **Tokens** | 000 |
| `hub_user_identities` | Hub | `hub_admin` | All (column-restricted) | Identity Core | **3rd-party IDs** | 000 |
| `hub_user_profiles` | Hub | `hub_admin` | All | Identity Core | **Avatar, timezone** | 000 |
| `hub_oauth_states` | Hub | `hub_admin` | Identity Core | Identity Core | **OAuth state** | 000 |
| `hub_temp_passwords` | Hub | `hub_admin` | Identity Core | Identity Core | **Reset tokens** | 000 |
| `user_passkeys` | Auth Core | `hub_admin` | Identity Core | Identity Core | **WebAuthn credentials** | 049 |
| `user_access_tokens` | Auth Core | `hub_admin` | Router, Identity Core | Identity Core | **PAT tokens** | 048 |
| `community_access_tokens` | Auth Core | `hub_admin` | Router, Identity Core | Identity Core | **CAT tokens** | 048 |
| `tenants` | Multi-tenancy | `hub_admin` | All | Hub Admin | — | 058 |
| `tenant_admins` | Multi-tenancy | `hub_admin` | Hub Admin | Hub Admin | — | 058 |
| `tenant_settings` | Multi-tenancy | `hub_admin` | All | Hub Admin | — | 058 |
| `hub_settings` | Hub (KV store) | `hub_admin` | All | Hub Admin | — | 000 |
| `hub_channel_permission_overrides` | Auth Core | `hub_admin` | Router | Auth Core | — | 058 |

---

## Community Management (Community Core)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `communities` | Community Core | `mod_core_community` | All | Community Core | — | 000 |
| `community_members` | Community Core | `mod_core_community` | Community Core | Community Core | — | 000 |
| `community_servers` | Community Core | `mod_core_community` | Community Core, Router | Community Core | — | 000 |
| `community_roles` | Auth Core | `hub_admin` | All | Auth Core | — | 058 |
| `community_join_requests` | Auth Core | `hub_admin` | Community Core | Auth Core | — | 049 |
| `community_types` | Community Core | `hub_admin` | All | Hub Admin | — | 047 (enum) |
| `hub_modules` | Community Core | `mod_core_community` | All | Community Core | — | 000 |
| `hub_module_installations` | Community Core | `mod_core_community` | All | Community Core | — | 000 |
| `hub_module_reviews` | Community Core | `mod_core_community` | All | Community Core | — | 000 |
| `platform_configs` | Community Core | `hub_admin` | All | Hub Admin | — | 000 |

---

## Routing & Command System (Router Module, Command Core)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `commands` | Router | `mod_router` | All | Router | — | 000 |
| `command_aliases` | Interactive (Alias) | `mod_interactive_alias` | All | Interactive Alias | — | 000 |
| `entities` | Router | `mod_router` | All | Router | — | 000 |
| `command_permissions` | Router | `mod_router` | All | Router | — | 000 |
| `command_executions` | Router | `mod_router` | Security Core | Router | — | 000 |
| `rate_limits` | Router | `mod_router` | All | Router | — | 000 |
| `stringmatch` | Router | `mod_router` | Router | Router | — | 000 |
| `module_responses` | Router | `mod_router` | Router | Router | — | 000 |
| `coordination` | Router | `mod_router` | Router | Router | — | 000 |
| `servers` | Router | `mod_router` | Router, Community Core | Router | — | 000 |
| `collector_modules` | System (Collector) | `hub_admin` | Router | Hub Admin | — | 000 |
| `module_scopes` | Auth Core | `hub_admin` | All | Auth Core | — | 058 |
| `module_controls` | System Control | `hub_admin` | Router | Hub Admin | — | 000 |

---

## Gaming & Loyalty (Loyalty Core, PvP, Simple Games, Giveaway)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `loyalty_points` | Loyalty Core | `mod_interactive_loyalty` | All | Loyalty Core | — | 000 |
| `loyalty_feature_toggles` | Loyalty Core | `hub_admin` | All | Hub Admin | — | 016 |
| `pvp_match_history` | PvP | `mod_interactive_loyalty` | All | Loyalty Core | — | 016 |
| `game_items` | PvP | `mod_interactive_loyalty` | Loyalty Core | Loyalty Core | — | 016 |
| `player_game_inventory` | PvP | `mod_interactive_loyalty` | Loyalty Core | Loyalty Core | — | 016 |
| `player_game_loadouts` | PvP | `mod_interactive_loyalty` | Loyalty Core | Loyalty Core | — | 016 |
| `golden_ticket_config` | Giveaway | `hub_admin` | All | Hub Admin | — | 016 |
| `golden_ticket_holders` | Giveaway | `mod_interactive_loyalty` | All | Loyalty Core | — | 016 |
| `loyalty_simple_game_results` | Simple Games | `mod_interactive_loyalty` | All | Loyalty Core | — | 018 |
| `loyalty_simple_game_cooldowns` | Simple Games | `mod_interactive_loyalty` | Loyalty Core | Loyalty Core | — | 018 |
| `loyalty_giveaway_keys` | Giveaway | `mod_interactive_loyalty` | All | Loyalty Core | — | 040 |
| `loyalty_giveaway_winners` | Giveaway | `mod_interactive_loyalty` | All | Loyalty Core | — | 040 |

---

## Community Engagement (Shoutout, Quotes, Memories, Polling, Forms)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `shoutout_history` | Shoutout | `mod_interactive_shoutout` | All | Shoutout | — | 003 |
| `shoutout_templates` | Shoutout | `mod_interactive_shoutout` | All | Shoutout | — | 003 |
| `shoutout_config` | Shoutout | `hub_admin` | All | Hub Admin | — | 009 |
| `shoutout_command_permissions` | Shoutout | `hub_admin` | All | Hub Admin | — | 009 |
| `auto_shoutout_creators` | Shoutout | `hub_admin` | All | Hub Admin | — | 009 |
| `auto_shoutout_roles` | Shoutout | `hub_admin` | All | Hub Admin | — | 009 |
| `video_shoutout_history` | Shoutout | `mod_interactive_shoutout` | All | Shoutout | — | 009 |
| `quotes` | Quotes | `mod_interactive_quote` | All | Quotes | — | 015 |
| `memories` | Memories | `mod_interactive_memories` | All | Memories | — | 000 |
| `reminders` | Memories | `mod_interactive_memories` | Memories | Memories | — | 000 |
| `memory_reactions` | Memories | `mod_interactive_memories` | All | Memories | — | 000 |
| `memory_categories` | Memories | `mod_interactive_memories` | All | Memories | — | 000 |
| `community_polls` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |
| `poll_options` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |
| `poll_votes` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |
| `community_forms` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |
| `form_fields` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |
| `form_submissions` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |
| `form_field_values` | Engagement | `mod_core_engagement` | All | Engagement | — | 000 |

---

## Media & Streaming (Calendar, Video Proxy, Music, Clips)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `calendar_events` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 000 |
| `event_attendees` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 000 |
| `event_reminders` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 000 |
| `calendar_appointments` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 000 |
| `calendar_ticket_types` | Event Ticketing | `hub_admin` | All | Hub Admin | — | 024 |
| `calendar_tickets` | Event Ticketing | `hub_admin` | All | Hub Admin | **Payment info** | 024 |
| `calendar_ticket_check_ins` | Event Ticketing | `hub_admin` | All | Hub Admin | — | 024 |
| `calendar_payment_config` | Event Ticketing | `hub_admin` | Hub Admin | Hub Admin | **Payment creds** | 024 |
| `calendar_event_admins` | Event Ticketing | `hub_admin` | All | Hub Admin | — | 024 |
| `calendar_sync_configs` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 061 |
| `community_calendar_subscriptions` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 061 |
| `calendar_event_sync_map` | Calendar | `mod_interactive_calendar` | All | Calendar | — | 061 |
| `video_stream_configs` | Video Proxy | `mod_core_video_proxy` | All | Video Proxy | — | 000 |
| `video_stream_destinations` | Video Proxy | `mod_core_video_proxy` | All | Video Proxy | — | 000 |
| `video_stream_sessions` | Video Proxy | `mod_core_video_proxy` | All | Video Proxy | — | 000 |
| `community_call_rooms` | Video Proxy (RTC) | `mod_core_rtc` | All | RTC | — | 000 |
| `community_call_participants` | Video Proxy (RTC) | `mod_core_rtc` | All | RTC | — | 000 |
| `call_raised_hands` | Video Proxy (RTC) | `mod_core_rtc` | All | RTC | — | 000 |
| `call_annotations` | Video Proxy (RTC) | `mod_core_rtc` | All | RTC | — | 000 |
| `video_feature_usage` | Video Proxy | `mod_core_video_proxy` | All | Video Proxy | — | 000 |
| `music_provider_config` | Music | `hub_admin` | All | Hub Admin | — | 012 |
| `music_radio_state` | Music | `mod_interactive_ytmusic`, `mod_interactive_spotify` | Music modules | Music modules | — | 012 |
| `music_queue` | Music | `mod_interactive_ytmusic`, `mod_interactive_spotify` | Music modules | Music modules | — | 012 |
| `youtube_now_playing` | Music | `mod_interactive_ytmusic` | All | Music (YT) | — | 000 |
| `youtube_search_cache` | Music | `mod_interactive_ytmusic` | All | Music (YT) | — | 000 |
| `youtube_activity` | Music | `mod_interactive_ytmusic` | All | Music (YT) | — | 000 |
| `spotify_tokens` | Music | `mod_interactive_spotify` | Spotify module | Spotify module | **OAuth tokens** | 000 |
| `spotify_now_playing` | Music | `mod_interactive_spotify` | All | Music (Spotify) | — | 000 |
| `spotify_search_cache` | Music | `mod_interactive_spotify` | All | Music (Spotify) | — | 000 |
| `clip_bookmarks` | Clips | `mod_core_engagement` | Engagement | Engagement | — | 042 |
| `clip_highlight_reels` | Clips | `mod_core_engagement` | Engagement | Engagement | — | 042 |

---

## Marketplace & Vendors (Marketplace, Vendor Modules)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `marketplace_modules` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_submissions` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_subscriptions` | Marketplace | `hub_admin` | All | Marketplace | **Payment info** | 017 |
| `marketplace_payments` | Marketplace | `hub_admin` | All | Marketplace | **Payment records** | 017 |
| `marketplace_premium_offerings` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_premium_subscriptions` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_reviews` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_settings` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_tc_acceptance` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `marketplace_sellers` | Marketplace | `hub_admin` | All | Marketplace | — | 017 |
| `community_premium_subscriptions` | Marketplace (Premium) | `hub_admin` | All | Marketplace | — | 059 |
| `vendor_submissions` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `vendor_submission_scopes` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `vendor_submission_reviews` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `vendor_submission_status_log` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `approved_vendor_modules` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `community_vendor_installations` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `vendor_module_reviews` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `vendor_payments` | Vendor Modules | `hub_admin` | All | Vendor | **Payment records** | 021 |
| `vendor_module_events` | Vendor Modules | `hub_admin` | All | Vendor | — | 021 |
| `vendor_role_requests` | Vendor Modules | `hub_admin` | All | Vendor | — | 023 |

---

## Platform Integrations (Credential Manager + Trigger/Action Modules)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration | RLS |
|---|---|---|---|---|---|---|---|
| `platform_integrations` | Credential Mgr | `mod_credential_manager` | Per-platform (RLS) | Credential Mgr + per-platform | **OAuth tokens, secrets** | 000 | FORCE |
| `credential_access_log` | Credential Mgr | `mod_credential_manager` | Per-role (RLS) | All modules | — | 000 | YES |
| `twitch_actions` | Twitch Action | `mod_action_twitch` | Action (Twitch) | Action (Twitch) | — | 000 | |
| `discord_actions` | Discord Action | `mod_action_discord` | Action (Discord) | Action (Discord) | — | 000 | |
| `slack_actions` | Slack Action | `mod_action_slack` | Action (Slack) | Action (Slack) | — | 000 | |
| `youtube_oauth_tokens` | YouTube Action | `mod_action_youtube` | Action (YouTube) | Action (YouTube) | **OAuth tokens** | 000 | |
| `teams_actions` | Teams Action | `mod_action_teams` | Action (Teams) | Action (Teams) | — | 000 | |
| `mattermost_action_history` | Mattermost Action | `hub_admin` | All | Hub Admin | — | 000 | |
| `googlechat_actions` | GoogleChat Action | `mod_action_googlechat` | Action (GChat) | Action (GChat) | — | 000 | |
| `lambda_invocations` | Lambda Action | `mod_action_lambda` | Action (Lambda) | Action (Lambda) | — | 000 | |
| `gcp_function_invocations` | GCP Functions Action | `mod_action_gcp` | Action (GCP) | Action (GCP) | — | 000 | |
| `openwhisk_action_executions` | OpenWhisk Action | `hub_admin` | All | Hub Admin | — | 000 | |

---

## Security, Analytics & Operations (Security Core, Analytics, Admin)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `activity_watch_sessions` | Activity Tracking | `mod_core_analytics` | Security Core, Analytics | Activity Tracking | — | 044 |
| `activity_message_events` | Activity Tracking | `mod_core_analytics` | Security Core, Analytics | Activity Tracking | — | 044 |
| `activity_stats_daily` | Activity Tracking | `mod_core_analytics` | All | Activity Tracking | — | 044 |
| `bot_detection_results` | Bot Detection | `hub_admin` | All | Hub Admin | — | 045 |
| `community_reputation_config` | Reputation | `hub_admin` | All | Hub Admin | — | 045 |
| `ai_researcher_config` | AI Researcher | `hub_admin` | All | Hub Admin | — | 045 |
| `ai_insights` | AI Research | `mod_core_ai_researcher`, `mod_interactive_ai` | All | AI Research modules | — | 005 |
| `analytics_bot_scores` | Analytics | `mod_core_analytics` | Analytics | Analytics | — | 000 |
| `analytics_suspected_bots` | Analytics | `mod_core_analytics` | Analytics | Analytics | — | 000 |
| `platform_analytics_snapshots` | Analytics | `mod_core_analytics` | All (view) | Analytics | — | 056 |
| `rcon_command_log` | Server Manager | `hub_admin` | All | Server Manager | **Game admin actions** | 055 |
| `server_ban_sync` | Server Manager | `hub_admin` | All | Server Manager | — | 055 |
| `server_access_policies` | Server Manager | `hub_admin` | All | Server Manager | — | 055 |
| `server_access_log` | Server Manager | `hub_admin` | All | Server Manager | — | 055 |
| `server_status_configs` | Server Manager | `mod_core_engagement` | All | Server Manager | — | 055 |
| `server_status_events` | Server Manager | `mod_core_engagement` | All | Server Manager | — | 000 |
| `user_presence_settings` | Presence Sync | `mod_core_engagement` | All | Engagement | — | 060 |
| `presence_events_log` | Presence Sync | `mod_core_engagement` | All | Engagement | — | 060 |
| `data_deletion_requests` | GDPR (Privacy) | `hub_admin` | Hub Admin, Security Core | Privacy | — | 062 |

---

## Workflow & Automation (Workflow Core, LFG)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `workflow_definitions` | Workflow Core | `mod_core_workflow` | All | Workflow | — | 000 |
| `workflow_executions` | Workflow Core | `mod_core_workflow` | Workflow | Workflow | — | 000 |
| `workflow_node_executions` | Workflow Core | `mod_core_workflow` | Workflow | Workflow | — | 000 |
| `workflow_schedules` | Workflow Core | `mod_core_workflow` | All | Workflow | — | 000 |
| `workflow_permissions` | Workflow Core | `mod_core_workflow` | All | Workflow | — | 000 |
| `workflow_webhooks` | Workflow Core | `mod_core_workflow` | Workflow | Workflow | — | 000 |
| `workflow_audit_log` | Workflow Core | `mod_core_workflow` | All | Workflow | — | 000 |
| `workflow_templates` | Workflow Core | `mod_core_workflow` | All | Workflow | — | 000 |
| `lfg_posts` | Interactive (LFG) | `mod_core_engagement` | All | Engagement | — | 042 |
| `lfg_joins` | Interactive (LFG) | `mod_core_engagement` | All | Engagement | — | 042 |

---

## Core System & Infrastructure (Labels, Browser Source, Service Registry, Software Discovery)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `labels` | Labels Core | `mod_core_labels` | All | Labels | — | 000 |
| `entity_labels` | Labels Core | `mod_core_labels` | All | Labels | — | 000 |
| `services` | Service Registry | `hub_admin` | All | Hub Admin | — | 020 |
| `service_events` | Service Registry | `hub_admin` | All | Hub Admin | — | 020 |
| `software_repositories` | Software Discovery | `hub_admin` | All | Hub Admin | — | 019 |
| `software_dependencies` | Software Discovery | `hub_admin` | All | Hub Admin | — | 019 |
| `browser_source_config` | Browser Source | `mod_core_browser_source` | All | Browser Source | — | 000 |
| `mirror_groups` | Messaging | `hub_admin` | All | Hub Admin | — | 046 |
| `mirror_group_members` | Messaging | `hub_admin` | All | Hub Admin | — | 046 |
| `server_link_requests` | Admin (Linking) | `hub_admin` | All | Hub Admin | — | 046 |

---

## AI Features (AI Chatter Config, Cookies/Consent)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `community_ai_chatter_config` | AI Chatter | `hub_admin` | All | Hub Admin | — | 061 |
| `ai_chatter_rate_limit_state` | AI Chatter | `mod_core_engagement` | Engagement | Engagement | — | 061 |
| `cookie_policy_versions` | Hub (Privacy) | `hub_admin` | All | Hub Admin | — | 000 |
| `cookie_consent` | Hub (Privacy) | `hub_admin` | All | Hub Admin | — | 000 |
| `cookie_audit_log` | Hub (Privacy) | `hub_admin` | All | Hub Admin | **User consent tracking** | 000 |

---

## Inventory Management (Quartermaster Module)

| Table | Owning Module | Primary DB Account | Read Access | Write Access | Sensitive | Migration |
|---|---|---|---|---|---|---|
| `inventory_items` | Inventory | `mod_interactive_inventory` | All | Inventory | — | 000 |
| `inventory_checkouts` | Inventory | `mod_interactive_inventory` | All | Inventory | — | 000 |
| `inventory_log` | Inventory | `mod_interactive_inventory` | All | Inventory | — | 000 |

---

## Legend

| Column | Meaning |
|---|---|
| **Owning Module** | Module that creates/manages the table |
| **Primary DB Account** | The database role that owns the table and manages lifecycle |
| **Read Access** | Which modules can SELECT from this table |
| **Write Access** | Which modules can INSERT/UPDATE/DELETE |
| **Sensitive** | Data privacy flags (PII, credentials, tokens, etc.) |
| **Migration** | SQL migration file that created the table (e.g., `000` = base schema, `031` = security additions) |
| **RLS** | Row-Level Security enabled (FORCE = mandatory, YES = default) |

---

**Total Tables**: 100+ across 13 module groups
**Total Database Roles**: 36
**Sensitive Tables**: 12 (with PII, tokens, or payment info)
**RLS-Protected Tables**: 2 (platform_integrations, credential_access_log)

**See Also**: [docs/DATABASE.md](../DATABASE.md) for high-level overview, access patterns, and initialization flow.
