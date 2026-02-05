# Waddles Screenshots

This directory contains screenshots of the Waddles admin interface and features.

## Capturing Screenshots

### Option 1: Manual Screenshots

1. Start Waddles with docker-compose:
   ```bash
   docker-compose up -d
   ```

2. Access the admin portal at http://localhost:8060
   - Note: You may need to expose port 8060 in docker-compose.yml first

3. Login with default credentials:
   - Username: `admin@localhost`
   - Password: `admin123`

4. Take screenshots of key pages and save them here

### Option 2: Automated with Puppeteer

Run the automated screenshot capture script:

```bash
# Install dependencies
npm install

# Run the script (requires hub to be running and port 8060 exposed)
node scripts/capture-screenshots.cjs
```

Or use the Docker-based version that works with the internal network:

```bash
chmod +x scripts/capture-screenshots-docker.sh
./scripts/capture-screenshots-docker.sh
```

## Screenshots Needed

- [ ] `login.png` - Login page
- [ ] `dashboard.png` - Main dashboard
- [ ] `communities.png` - Communities list
- [ ] `community-dashboard.png` - Individual community dashboard
- [ ] `servers.png` - Server/channel configuration
- [ ] `routes.png` - Command routes
- [ ] `modules.png` - Module registry
- [ ] `users.png` - User management
- [ ] `settings.png` - Account settings

## Adding Screenshots to README

Once screenshots are captured, update the main README.md to include them:

```markdown
## Screenshots

### Dashboard
![Dashboard](docs/screenshots/dashboard.png)

### Community Management
![Communities](docs/screenshots/communities.png)

### Module Registry
![Modules](docs/screenshots/modules.png)
```
