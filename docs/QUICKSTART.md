# Waddles Quick Start Guide

Get Waddles running in minutes with this comprehensive quick start guide.

## Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

- **Docker**: Version 20.04 or higher ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: Version 2.0 or higher (included with Docker Desktop)
- **Git**: For cloning the repository

### Minimum System Requirements

- **CPU**: 4 cores
- **RAM**: 8 GB minimum, 16 GB recommended
- **Disk Space**: 50 GB minimum, 100 GB recommended
- **Operating System**: Linux, macOS, or Windows with WSL2

### Platform API Credentials (Optional for First Run)

To connect Waddles to your platforms, you'll need:

- **Twitch**: App ID, App Secret, Webhook Secret ([Create Twitch App](https://dev.twitch.tv/console/apps))
- **Discord**: Bot Token, Application ID, Public Key ([Create Discord App](https://discord.com/developers/applications))
- **Slack**: Bot Token, App Token, Signing Secret ([Create Slack App](https://api.slack.com/apps))
- **YouTube**: API Key, Client ID, Client Secret ([Google Cloud Console](https://console.cloud.google.com/))

## Quick Start with Docker Compose

### Step 1: Clone the Repository

```bash
git clone https://github.com/waddlebot/waddlebot.git
cd waddlebot
```

### Step 2: Configure Environment Variables

Create your environment configuration file:

```bash
cp .env.example .env
```

Edit `.env` with your preferred text editor. **Minimum required changes:**

```bash
# Database password (change this!)
POSTGRES_PASSWORD=your_secure_password_here

# Redis password (change this!)
REDIS_PASSWORD=your_secure_redis_password

# JWT secret for authentication (change this!)
JWT_SECRET=your_secure_jwt_secret_key_here

# MinIO credentials (change these!)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=your_secure_minio_password

# Service API key (change this!)
SERVICE_API_KEY=your_secure_service_api_key

# Kong configuration (change these!)
KONG_PG_PASSWORD=your_secure_kong_password
KONG_SESSION_SECRET=your_secure_kong_session_secret
```

**Optional Platform Credentials** (add these to connect to platforms):

```bash
# Twitch
TWITCH_CLIENT_ID=your_twitch_client_id
TWITCH_CLIENT_SECRET=your_twitch_client_secret
TWITCH_WEBHOOK_SECRET=your_webhook_secret

# Discord
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_APPLICATION_ID=your_discord_app_id
DISCORD_CLIENT_ID=your_discord_client_id
DISCORD_CLIENT_SECRET=your_discord_client_secret

# Slack
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your_signing_secret
SLACK_CLIENT_ID=your_slack_client_id
SLACK_CLIENT_SECRET=your_slack_client_secret
```

### Step 3: Create Required Directories

```bash
# Create log directory
sudo mkdir -p /var/log/waddlebotlog
sudo chown $USER:$USER /var/log/waddlebotlog
```

### Step 4: Start WaddleBot

```bash
# Start all services
docker-compose up -d

# Wait for services to start (this may take 2-3 minutes)
docker-compose ps
```

### Step 5: Verify Installation

Check that all services are running:

```bash
# View service status
docker-compose ps

# All services should show STATE: Up
# Example output:
# NAME                    SERVICE        STATUS
# waddlebot-postgres      postgres       Up
# waddlebot-redis         redis          Up
# waddlebot-router        router         Up
# waddlebot-hub           hub            Up
# ...
```

Check service health:

```bash
# Check router health
curl http://localhost:8000/health

# Check hub health
curl http://localhost:8060/health

# Expected response: {"status":"healthy",...}
```

### Step 6: Access the Admin Portal

Open your browser and navigate to:

**http://localhost:8060**

**Default Login Credentials:**
- Email: `admin@localhost`
- Password: `admin123`

**IMPORTANT:** Change the default password immediately after first login!

## First-Time Configuration

### 1. Create Your First Community

After logging in:

1. Navigate to **Communities** in the sidebar
2. Click **Create Community**
3. Fill in the details:
   - **Name**: Your community name
   - **Description**: Brief description
   - **Settings**: Configure defaults
4. Click **Create**

### 2. Configure Platform Connections

#### Twitch Integration

1. Go to **Settings** → **Platforms** → **Twitch**
2. Enter your Twitch credentials:
   - Client ID
   - Client Secret
   - Webhook Secret
3. Click **Connect**
4. Complete OAuth flow
5. Select channels to monitor

#### Discord Integration

1. Go to **Settings** → **Platforms** → **Discord**
2. Enter your Discord bot token
3. Click **Connect**
4. Invite bot to your Discord server using the provided OAuth URL
5. Configure command prefix and permissions

#### Slack Integration

1. Go to **Settings** → **Platforms** → **Slack**
2. Enter your Slack credentials:
   - Bot Token
   - App Token
   - Signing Secret
3. Click **Connect**
4. Install app to your workspace

### 3. Enable Modules

Navigate to **Modules** in the admin panel:

1. **AI Interaction**: Enable for AI chat responses
   - Configure AI provider (Ollama, OpenAI, or MCP)
   - Set system prompt
   - Configure response triggers

2. **Loyalty System**: Enable virtual currency
   - Set earning rates
   - Configure minigames (slots, coinflip, roulette)
   - Enable duels

3. **Music Integration**: Enable for music requests
   - Configure YouTube Music
   - Configure Spotify (requires Premium)
   - Set up OBS browser source

4. **Other Modules**: Enable as needed
   - Calendar (event scheduling)
   - Inventory (item management)
   - Memories (community quotes)
   - Shoutouts (highlight users)

### 4. Configure Commands

1. Go to **Commands** in the admin panel
2. View available commands by module
3. Customize command aliases
4. Set command permissions
5. Enable/disable specific commands

### 5. Set Up OBS Integration (Optional)

For streamers who want overlays:

1. Navigate to **OBS Integration** → **Overlays**
2. Generate overlay URLs for:
   - Now Playing (music)
   - Recent Events
   - Chat Display
   - Custom Alerts
3. Add Browser Source in OBS:
   - Copy overlay URL
   - Add Browser Source in OBS
   - Paste URL
   - Set dimensions (1920x1080 recommended)

## Docker Compose Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a specific service
docker-compose restart hub

# View logs
docker-compose logs -f router
docker-compose logs -f hub

# View logs for all services
docker-compose logs -f

# Rebuild and restart services
docker-compose up -d --build
```

### Database Management

```bash
# Access PostgreSQL shell
docker-compose exec postgres psql -U waddlebot -d waddlebot

# Create database backup
docker-compose exec postgres pg_dump -U waddlebot waddlebot > backup.sql

# Restore database
docker-compose exec -T postgres psql -U waddlebot waddlebot < backup.sql

# View database logs
docker-compose logs postgres
```

### Redis Management

```bash
# Access Redis CLI
docker-compose exec redis redis-cli -a your_redis_password

# View Redis logs
docker-compose logs redis

# Clear Redis cache
docker-compose exec redis redis-cli -a your_redis_password FLUSHALL
```

### Troubleshooting Commands

```bash
# Check container status
docker-compose ps

# View resource usage
docker stats

# Remove all stopped containers and volumes
docker-compose down -v

# Rebuild everything from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

## Next Steps

Now that WaddleBot is running, explore these resources:

- **[Architecture Guide](ARCHITECTURE.md)**: Understand WaddleBot's microservices architecture
- **[Module Documentation](module-details-core.md)**: Learn about available modules
- **[API Reference](reference/api-reference.md)**: Integrate with WaddleBot's APIs
- **[Development Guide](reference/development-rules.md)**: Build custom modules
- **[Kubernetes Deployment](../k8s/QUICKSTART.md)**: Deploy to production with Kubernetes

## Common Issues

### Port Already in Use

If you see errors about ports already in use:

```bash
# Check what's using the ports
sudo lsof -i :8060  # Hub
sudo lsof -i :8000  # Router
sudo lsof -i :5432  # PostgreSQL

# Change ports in docker-compose.yml if needed
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Verify password in .env matches
grep POSTGRES_PASSWORD .env
```

### Containers Keep Restarting

```bash
# View container logs
docker-compose logs <service-name>

# Check for common issues:
# - Missing environment variables
# - Database not ready
# - Port conflicts
# - Insufficient resources
```

### Cannot Access Admin Portal

```bash
# Verify hub is running
docker-compose ps hub

# Check hub logs
docker-compose logs hub

# Verify port mapping
docker-compose port hub 8060

# Try accessing directly
curl http://localhost:8060/health
```

### Services Won't Start

```bash
# Check available disk space
df -h

# Check available memory
free -h

# Verify Docker is running
docker ps

# Check Docker logs
docker-compose logs
```

## Security Considerations

### Change Default Credentials

**Immediately change these after installation:**

1. Admin portal password
2. Database passwords in `.env`
3. JWT secrets
4. API keys

### Production Deployment

For production use:

1. **Use HTTPS/TLS**: Configure SSL certificates
2. **Firewall**: Restrict access to admin portal
3. **Secrets Management**: Use Docker secrets or environment variable encryption
4. **Regular Backups**: Automated database backups
5. **Monitoring**: Set up Prometheus/Grafana
6. **Updates**: Keep Docker images updated

### Network Security

By default, WaddleBot uses network isolation:

- **Internal Network**: Database, Redis, inter-service communication
- **Public Network**: Only hub, browser sources, and API gateway exposed
- **Kong Gateway**: Rate limiting and API protection

## Support

### Getting Help

- **Documentation**: Browse `/docs` directory
- **GitHub Issues**: Report bugs at https://github.com/waddlebot/waddlebot/issues
- **Community**: Join our Discord (coming soon)

### Logs and Debugging

When reporting issues, include:

```bash
# Collect logs
docker-compose logs > waddlebot-logs.txt

# System information
docker version
docker-compose version
uname -a
```

---

**Ready for production?** Check out our [Kubernetes Deployment Guide](../k8s/QUICKSTART.md) for enterprise-grade deployment with high availability, auto-scaling, and monitoring.
