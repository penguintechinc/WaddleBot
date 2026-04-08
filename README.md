# Waddles

> **Next-Generation Multi-Platform Bot Framework**
>
> Build powerful chatbots for Twitch, Discord, Slack, YouTube, and more with AI, loyalty systems, and enterprise-grade deployment options.

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Version](https://img.shields.io/badge/version-2.0.1-green.svg)](#version-management)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/kubernetes-ready-blue.svg)](https://kubernetes.io/)

---

## Why Waddles?

**For Streamers & Communities:**
- Engage your audience with AI-powered chat, loyalty points, and interactive minigames
- Support multiple platforms from one place (Twitch, Discord, Slack, YouTube, Kick)
- Built-in features: giveaways, duels, music requests, event calendars, and more

**For Developers:**
- Modern microservices architecture with clean APIs
- Easy to extend with new modules and commands
- Comprehensive documentation and examples
- Production-ready with Kubernetes and CI/CD

**For Businesses:**
- Enterprise deployment options with high availability
- RBAC, audit logging, and security best practices
- Multi-tenant support for managing multiple communities
- Prometheus metrics and observability built-in

## Quick Start

### Deploy to Kubernetes (recommended)

```bash
git clone https://github.com/penguintechinc/waddlebot.git
cd waddlebot

# Alpha (local MicroK8s)
kubectl apply --context local-alpha -k k8s/kustomize/overlays/alpha

# Beta / Production (Helm)
helm install waddlebot ./k8s/helm/waddlebot -n waddlebot --create-namespace \
  -f k8s/helm/waddlebot/values-beta.yaml
```

**See [docs/QUICKSTART.md](docs/QUICKSTART.md) for full deployment guide.**

### Access the Admin Portal

- **Alpha:** `https://waddles.localhost.local`
- **Beta:** `https://waddlebot.penguintech.cloud`
- **Production:** `https://waddles.app`

## Key Features

### Out-of-the-Box Modules

| Feature | Description |
|---------|-------------|
| **AI Chat** | Intelligent responses powered by Ollama, OpenAI, or MCP |
| **Loyalty System** | Virtual currency, earning configs, leaderboards |
| **Minigames** | Slots, coinflip, roulette with betting |
| **Duels** | PvP wagering with gear bonuses |
| **Giveaways** | Reputation-weighted prize system |
| **Music** | Spotify & YouTube Music with OBS integration |
| **Calendar** | Event scheduling with approval workflows |
| **Shoutouts** | Highlight users across platforms |
| **Inventory** | Item management system |
| **Memories** | Community quotes and reminders |
| **Announcements** | Broadcast to hub and all platforms |
| **Workflows** | Visual workflow builder with event triggers and actions (1 per community free, unlimited premium) |
| **Browser Sources** | OBS overlays, captions, tickers, and alerts |
| **Reputation** | FICO-style scoring (300-850) with auto-moderation |
| **Server Manager** | RCON integration for game server management |

### Platform Support

- **Twitch** - EventSub webhooks, IRC chat, OAuth
- **Discord** - Bot events, slash commands
- **Slack** - Events API, slash commands
- **YouTube Live** - Live chat, SuperChat
- **Kick** - Webhook integration
- **Microsoft Teams** - Bot Framework webhook
- **Mattermost** - Webhook events, slash commands
- **Google Chat** - Events API

### Architecture (v2.2.x — 22 Containers)

```
Platform Events (Twitch, Discord, Slack, YouTube, Kick, Teams, Mattermost, Google Chat)
        |
   Trigger Services
   ├── trigger-discord         (persistent WebSocket bot)
   ├── trigger-streaming       (Twitch IRC + YouTube + Kick pollers)
   └── trigger-webhooks        (Slack + Teams + Mattermost + Google Chat HTTP)
        |
   Router Module (Command Processing & Event Gateway)
        |
   ┌────────────────────────────────────────────────┐
   │              Interactive Services               │
   ├── interactive-social      (alias, shoutout, presence, quotes)
   ├── interactive-loyalty     (loyalty points, minigames, duels)
   ├── interactive-gaming      (LFG, inventory, server manager)
   ├── interactive-media       (clips, Spotify, YouTube Music)
   ├── interactive-productivity(calendar, memories, translate)
   └── interactive-ai          (AI chat, WaddleAI integration)
   └────────────────────────────────────────────────┘
        |
   ┌────────────────────────────────────────────────┐
   │               Core Services                     │
   ├── core-data               (analytics, engagement, reputation, labels)
   ├── core-identity           (identity, security, credentials)
   └── core-community          (community mgmt, workflows, browser source, video proxy)
   └────────────────────────────────────────────────┘
        |
   ┌────────────────────────────────────────────────┐
   │              Action Services                    │
   ├── action-discord          (Discord message sender)
   ├── action-platforms        (Slack + Teams + Mattermost + Google Chat + Twitch + YouTube)
   └── action-serverless       (Lambda + OpenWhisk + GCP Functions)
   └────────────────────────────────────────────────┘
        |
   Infrastructure (PostgreSQL, Redis, MinIO, Qdrant)
```

Plus: **hub-api** (admin portal backend), **hub-webui** (React admin frontend), **marketplace**, **ai-researcher**, **migrations** (K8s Job).

**Full architecture diagram:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Screenshots

> Regenerate with `node scripts/capture-screenshots.cjs` (requires hub backend + frontend on port 8060).

### User Dashboard
![User Dashboard](docs/screenshots/dashboard.png)
![User Profile](docs/screenshots/dashboard-profile.png)
![User Settings](docs/screenshots/dashboard-settings.png)

### Community Portal
![Communities List](docs/screenshots/communities.png)
![Community Dashboard](docs/screenshots/community-dashboard.png)
![Community Chat](docs/screenshots/community-chat.png)
![Community Leaderboard](docs/screenshots/community-leaderboard.png)
![Community Members](docs/screenshots/community-members.png)
![Community Settings](docs/screenshots/community-settings.png)

### Admin Panel
![Admin Overview](docs/screenshots/admin-overview.png)
![Admin Members](docs/screenshots/admin-members.png)
![Admin Servers](docs/screenshots/admin-servers.png)
![Admin Modules](docs/screenshots/admin-modules.png)
![Admin AI Insights](docs/screenshots/admin-ai-insights.png)
![Admin Marketplace](docs/screenshots/admin-marketplace.png)
![Admin Reputation](docs/screenshots/admin-reputation.png)
![Admin Domains](docs/screenshots/admin-domains.png)
![Admin Mirror Groups](docs/screenshots/admin-mirror-groups.png)
![Admin Community Profile](docs/screenshots/admin-community-profile.png)

### Premium Features
![AI Config](docs/screenshots/admin-ai-config.png) `PREMIUM`
![Workflows](docs/screenshots/admin-workflows.png) `PREMIUM`
![Browser Sources](docs/screenshots/admin-browser-sources.png) `PREMIUM`
![Leaderboard Config](docs/screenshots/admin-leaderboard-config.png) `PREMIUM`

### Super Admin
![Super Admin Dashboard](docs/screenshots/superadmin-dashboard.png)
![Community Management](docs/screenshots/superadmin-communities.png)

## Version Management

**Current:** See `.version` file. Format: `vMajor.Minor.Patch.build`

```bash
./scripts/version/update-version.sh          # Update build timestamp
./scripts/version/update-version.sh patch    # Increment patch
./scripts/version/update-version.sh minor    # Increment minor
./scripts/version/update-version.sh major    # Increment major
```

## Licensing & Tiers

Waddles is open source (GPL-3.0) and free to use with basic features:

**Free Tier (Open Source)**
- All core features included
- 1 workflow per community
- Broadcast announcements to all connected platforms
- Full community management

**Premium Tier**
- Unlimited workflows per community
- Advanced analytics and AI insights
- Browser source overlays and captions
- Custom raffle sounds and messages
- Priority support

## Documentation

| Guide | Description |
|-------|-------------|
| **[Quick Start](docs/QUICKSTART.md)** | Installation and first-time setup |
| **[Architecture](docs/ARCHITECTURE.md)** | System design and component overview |
| **[Kubernetes](docs/KUBERNETES.md)** | K8s deployment, Helm, Kustomize |
| **[Database](docs/DATABASE.md)** | Schema, migrations, per-service accounts |
| **[Contributing](docs/CONTRIBUTING.md)** | Building new modules and contributing |
| **[Security](docs/SECURITY.md)** | Security policy and reporting |
| **[Workflows](docs/WORKFLOWS.md)** | Workflow builder documentation |
| **[Platform Commands](docs/platform-commands.md)** | Command reference per platform |
| **[Credentials Rotation](docs/CREDENTIALS-ROTATION-CHECKLIST.md)** | Credential rotation checklist |
| **[Changelog](CHANGELOG.md)** | Version history |

**Browse all docs:** [/docs](docs/)

## Technology Stack

**Backend:** Python 3.13, Quart (async), PostgreSQL, Redis
**Frontend:** React 18, Vite, TailwindCSS v4
**Infrastructure:** Docker, Kubernetes (Helm v3 + Kustomize), GitHub Actions
**AI/LLM:** Ollama, OpenAI, MCP providers
**Storage:** PostgreSQL, MinIO (S3), Qdrant (vectors)

## License

**Open Source (GPL-3.0)** - Free for personal, internal, and educational use

**Commercial License** required for:
- SaaS/hosting services
- Commercial products embedding Waddles
- Managed services for clients

**Contributor Employer Exception:** Companies employing contributors get perpetual GPL-2.0 access to versions their employee contributed to.

See [LICENSE.md](LICENSE.md) for full terms.

## Community & Support

- **Documentation:** [/docs](docs/)
- **Issues:** [GitHub Issues](https://github.com/penguintechinc/waddlebot/issues)
- **Company:** [www.penguintech.io](https://www.penguintech.io)
- **Email:** support@penguintech.io

## Contributing

We welcome contributions! See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

---

**Made with care by [Penguin Tech Inc](https://www.penguintech.io)**
