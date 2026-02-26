# Waddles Attribution

This file acknowledges the libraries, contributors, reviewers, beta testers, and community members who have helped make Waddles possible.

---

## Core Libraries & Frameworks

### Backend (Python)
| Library | License | Purpose |
|---------|---------|---------|
| [Quart](https://github.com/pallets/quart) | MIT | Async web framework |
| [Hypercorn](https://github.com/pgjones/hypercorn) | MIT | ASGI server |
| [SQLAlchemy](https://www.sqlalchemy.org/) | MIT | Database ORM |
| [asyncpg](https://github.com/MagicStack/asyncpg) | Apache 2.0 | PostgreSQL async driver |
| [redis-py](https://github.com/redis/redis-py) | MIT | Redis client |
| [grpcio](https://grpc.io/) | Apache 2.0 | gRPC framework |
| [Pydantic](https://pydantic-docs.helpmanual.io/) | MIT | Data validation |
| [httpx](https://www.python-httpx.org/) | BSD | Async HTTP client |
| [APScheduler](https://apscheduler.readthedocs.io/) | MIT | Task scheduling |

### Backend (Node.js)
| Library | License | Purpose |
|---------|---------|---------|
| [Express](https://expressjs.com/) | MIT | Web framework |
| [Sequelize](https://sequelize.org/) | MIT | Database ORM |
| [jsonwebtoken](https://github.com/auth0/node-jsonwebtoken) | MIT | JWT authentication |
| [bcrypt](https://github.com/kelektiv/node.bcrypt.js) | MIT | Password hashing |
| [socket.io](https://socket.io/) | MIT | WebSocket communication |

### Frontend (React)
| Library | License | Purpose |
|---------|---------|---------|
| [React](https://reactjs.org/) | MIT | UI framework |
| [React Router](https://reactrouter.com/) | MIT | Client-side routing |
| [Tailwind CSS](https://tailwindcss.com/) | MIT | Utility-first CSS |
| [Axios](https://axios-http.com/) | MIT | HTTP client |
| [React Query](https://tanstack.com/query) | MIT | Data fetching |

### Infrastructure
| Technology | License | Purpose |
|------------|---------|---------|
| [PostgreSQL](https://www.postgresql.org/) | PostgreSQL License | Primary database |
| [Redis](https://redis.io/) | BSD | Caching & message queue |
| [Docker](https://www.docker.com/) | Apache 2.0 | Containerization |
| [Kong](https://konghq.com/) | Apache 2.0 | API Gateway |
| [Nginx](https://nginx.org/) | BSD | Reverse proxy |

### Platform Integrations
| Platform | API | Purpose |
|----------|-----|---------|
| [Twitch](https://dev.twitch.tv/) | Twitch API | Chat & events |
| [Discord](https://discord.com/developers/) | Discord API | Bot integration |
| [Slack](https://api.slack.com/) | Slack API | Workspace integration |
| [YouTube](https://developers.google.com/youtube/) | YouTube Data API | Video & chat |
| [Spotify](https://developer.spotify.com/) | Spotify Web API | Music playback |

---

## Feature Contributors

### Quartermaster (Inventory System)
**Idea Contributor**: NicAtNight

The Quartermaster module - Waddles's asset tracking and checkout system - was inspired by and named at the request of NicAtNight. This feature enables communities to:
- Track community assets (in-game items, equipment, resources)
- Manage checkouts with due dates and notifications
- Integrate with community currency for checkout pricing
- Search and browse inventory through the Hub WebUI

### Translation Module
**Idea Contributor**: Velocity69DJ

The Translation module - enabling real-time chat translation and caption overlays for streams - was suggested by Velocity69DJ. This feature enables:
- Real-time translation of chat messages between languages
- Caption overlays for OBS browser sources
- Multi-language support for international communities
- Configurable translation providers

---

## Contributors

*Contributors who have submitted code, documentation, or significant improvements.*

<!-- Add contributors here as they contribute -->
<!-- Format: | [@username](github-link) | Description of contribution | -->

| Contributor | Contributions |
|-------------|---------------|
| ArcherPupper | Initial architecture support |
| thysw95 | Initial code support support |

---

## Reviewers

*Individuals who have helped review code, architecture, or documentation.*

<!-- Add reviewers here -->

| Reviewer | Areas |
|----------|-------|
| Apollonaut | Initial reviewer and feedback on discord integration, recommended PyCord utilization instead of discordpy |

---

## Beta Testers

*Community members who tested pre-release versions and provided feedback.*

<!-- Add beta testers here -->

| Tester | Feedback Areas |
|--------|----------------|
| *Be the first beta tester!* | |

---

## Special Thanks

- The open-source community for the amazing libraries that make Waddles possible
- All the streamers and communities who trust Waddles to enhance their streams
- Everyone who has reported bugs, suggested features, or spread the word

---

## How to Get Credited

### Feature Ideas
If you've contributed an idea or feature to Waddles:
1. Open an issue on GitHub with your contribution details
2. Include your preferred name/handle for attribution
3. Describe the feature or idea you contributed

### Code Contributions
All code contributors are automatically credited via git history. To be listed in this file:
1. Submit a pull request with your contribution
2. Add yourself to the Contributors section

### Beta Testing
To become a beta tester:
1. Join our Discord server (link in README)
2. Request access to the beta testing channel
3. Provide feedback on pre-release versions

---

*Last updated: December 2025*
