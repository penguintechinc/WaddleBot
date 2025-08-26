# WaddleBot Usage Guide

This guide covers how to build, configure, and run WaddleBot's various Docker containers and applications.

## Overview

WaddleBot uses a microservices architecture with multiple Docker containers:

- **Core Services**: Router, Identity, Portal, Marketplace
- **Collector Modules**: Twitch, Discord, Slack platform integrations  
- **Interaction Modules**: AI, Alias, Shoutout, Inventory, Calendar, Memories
- **Media Modules**: YouTube Music, Spotify, Browser Source
- **Infrastructure**: Kong Gateway, PostgreSQL, Redis

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database
- Redis server
- Platform API credentials (Twitch, Discord, Slack)

### Quick Start

1. **Copy environment template:**
```bash
cp .env.example .env
```

2. **Configure your `.env` file** with your database credentials, API keys, and platform tokens

3. **Start the core services:**
```bash
docker-compose up -d db redis kong
```

4. **Deploy your desired modules:**
```bash
docker-compose up -d router identity-core twitch-collector discord-collector
```

For detailed configuration of each module, environment variables, build options, and deployment strategies, see the [comprehensive USAGE documentation](docs/USAGE.md). 

