# Clip Interaction Module - Release Notes

Version history, breaking changes, migration guides, and upgrade instructions for the Clip Interaction Module.

## Version Format

`vX.Y.Z` where:
- **X (Major)**: Breaking API changes, removed features
- **Y (Minor)**: New features, non-breaking additions
- **Z (Patch)**: Bug fixes, security patches, documentation

Current Version: **v1.0.0** (Initial Release)

---

## v1.0.0 (2026-02-24)

### Initial Release

Complete implementation of clip interaction features for WaddleBot platform.

#### Features

**Clip Management**
- Bookmark clips from Twitch with metadata (game, tags)
- List bookmarked clips with filtering (game, tags, pagination)
- Update clip tags dynamically
- Unique constraint prevents duplicate bookmarks per community

**Highlight System**
- Mark clips as highlights for reel creation
- Filter and view only highlighted clips
- Query overlay data (5 latest highlights for OBS)

**Highlight Reels**
- Create reels from multiple highlighted clips
- Retrieve reel details with full clip metadata
- Publish reels for sharing
- Track reel creator and creation timestamp

**Twitch Integration**
- HTTP proxy pattern for clip creation via action-twitch
- Transparent error handling and logging

**OBS Overlay**
- Real-time highlight data for stream overlays
- Optimized for 5-second polling interval

#### API Endpoints

| Method | Endpoint | Status |
|--------|----------|--------|
| POST | `/api/v1/clips/{cid}/create` | Implemented |
| POST | `/api/v1/clips/{cid}/bookmark` | Implemented |
| GET | `/api/v1/clips/{cid}` | Implemented |
| PUT | `/api/v1/clips/{cid}/{clip_id}/tags` | Implemented |
| POST | `/api/v1/clips/{cid}/{clip_id}/highlight` | Implemented |
| POST | `/api/v1/reels/{cid}` | Implemented |
| GET | `/api/v1/reels/{cid}/{reel_id}` | Implemented |
| PUT | `/api/v1/reels/{cid}/{reel_id}/publish` | Implemented |
| GET | `/api/v1/overlay/{cid}` | Implemented |

#### Database Schema

- `clip_bookmarks`: Bookmark storage with unique constraint
- `clip_highlight_reels`: Reel metadata and clip ordering

#### Architecture

- Quart (async ASGI framework)
- PyDAL ORM for database abstraction
- httpx for async HTTP proxying
- Redis caching with TTL-based invalidation
- Middleware-based authentication

#### Dependencies

```
quart==0.18.4
hypercorn==0.14.4
httpx==0.24.1
pydal==20230612.1
python-dotenv==1.0.0
flask-core==1.0.0
```

#### Configuration

Environment variables for all settings:

```env
MODULE_PORT=8098
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
CORE_API_URL=http://core-api:8000
ROUTER_API_URL=http://router:8001
TWITCH_MODULE_URL=http://action-twitch:8010
LOG_LEVEL=INFO
SECRET_KEY=generated
CACHE_TTL_SECONDS=300
CLIP_RETENTION_DAYS=365
```

#### Documentation

- **OVERVIEW.md**: Module description, features, architecture
- **API.md**: Complete REST endpoint reference
- **USAGE.md**: Workflows, integration patterns, best practices
- **CONFIGURATION.md**: Environment variables, setup guides
- **ARCHITECTURE.md**: Design patterns, data flow, caching
- **TROUBLESHOOTING.md**: Common issues and solutions
- **RELEASE_NOTES.md**: Version history (this file)
- **TESTING.md**: Test suite and validation

#### Breaking Changes

None (initial release).

#### Deprecations

None (initial release).

#### Known Limitations

1. **Reel reordering**: Clips in reels maintain insertion order only; no drag-to-reorder
2. **Bulk operations**: No batch bookmark or reel operations (v1.1.0)
3. **Retention policy**: Hard delete of expired clips (soft delete in v1.1.0)
4. **Event async**: Event publishing blocks API response (queue-based in v1.1.0)
5. **Clip metadata**: Only Twitch clip ID stored; full data cached via Redis

#### Migration Guide

N/A (initial release). Start with production environment setup:

```bash
# 1. Deploy module
docker pull waddlebot-clip-interaction:v1.0.0
docker run -e MODULE_PORT=8098 -e DATABASE_URL=postgresql://... waddlebot-clip-interaction:v1.0.0

# 2. Run migrations
python3 scripts/migrate.py

# 3. Validate health
curl http://localhost:8098/health

# 4. Test endpoints
curl http://localhost:8098/api/v1/clips/community-id -H "Authorization: Bearer $TOKEN"
```

#### Contributors

- Penguin Tech Inc

#### Support

For v1.0.0 issues, contact: support@penguintech.io

---

## Planned Releases

### v1.1.0 (Scheduled: 2026-03-15)

#### Features

- **Batch Operations**: Bookmark multiple clips, create reels from tag filter
- **Soft Deletes**: Archive instead of hard delete, restore clips
- **Async Events**: Queue-based event publishing (non-blocking)
- **Reel Reordering**: Drag-to-reorder clips in reel editor
- **Export**: Download reel metadata as JSON/CSV

#### Improvements

- Caching layer optimization (reduce TTL, smarter invalidation)
- Query performance tuning (batch queries, lazy loading)
- Enhanced error messages with actionable guidance

#### Database Changes

```sql
-- Add archive support
ALTER TABLE clip_bookmarks ADD COLUMN archived_at TIMESTAMP;
ALTER TABLE clip_highlight_reels ADD COLUMN archived_at TIMESTAMP;

-- Add clip ordering
ALTER TABLE clip_highlight_reels ADD COLUMN clip_order JSONB;

-- Add export tracking
CREATE TABLE clip_exports (
  id UUID PRIMARY KEY,
  reel_id UUID REFERENCES clip_highlight_reels,
  exported_by UUID,
  format VARCHAR(10),
  created_at TIMESTAMP
);
```

#### API Changes

- `POST /api/v1/clips/{cid}/bookmark` → Support array in body for bulk
- `POST /api/v1/reels/{cid}/{rid}/reorder` → New endpoint for clip ordering
- `GET /api/v1/reels/{cid}/{rid}/export` → Export reel (JSON/CSV)

#### Breaking Changes

None planned.

### v1.2.0 (Scheduled: 2026-04-30)

#### Features

- **Search API**: Full-text search on clip titles, tags, games
- **Highlights Analytics**: Stats on most-highlighted games, peak highlight times
- **Reel Sharing**: Pre-generated share links with embed support
- **Comments/Notes**: Per-clip annotations, team collaboration

#### Database Changes

- Full-text search indexes on clip titles/tags
- Reel shares table with analytics
- Clip notes table

### v2.0.0 (Scheduled: 2026-06-30) - Major Release

#### Breaking Changes

- Change clip storage from PostgreSQL to dedicated video service (planned)
- Reel API response structure (pagination, metadata layout)
- Removal of deprecated clip metadata fields

#### Features

- **Video Integration**: Direct video streaming for clips
- **Metadata Enrichment**: AI-generated highlight descriptions
- **Smart Reels**: Auto-curated reels based on performance metrics
- **Collaboration**: Real-time reel editing with team members

---

## Upgrade Instructions

### From v1.0.0 to v1.1.0

#### Zero-Downtime Upgrade

1. **Deploy new version** (backward compatible):

```bash
docker pull waddlebot-clip-interaction:v1.1.0
# New version can run alongside v1.0.0
```

2. **Run migrations** (safe to run before traffic shift):

```bash
python3 scripts/migrate.py --target v1.1.0
```

3. **Shift traffic gradually** (canary deployment):

```yaml
# Kubernetes canary
spec:
  strategy:
    canary:
      steps:
      - weight: 10  # 10% to v1.1.0
      - weight: 50  # 50% after 5 mins
      - weight: 100 # 100% after 10 mins
```

4. **Verify migration success**:

```bash
# Check for archive columns
psql $DATABASE_URL -c "\d clip_bookmarks" | grep archived_at

# Test batch bookmark endpoint
curl -X POST http://localhost:8098/api/v1/clips/community-id/batch-bookmark \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clips":[...]}'
```

5. **Rollback if needed**:

```bash
# Immediate rollback to v1.0.0
kubectl set image deployment/clip-interaction \
  clip-interaction=waddlebot-clip-interaction:v1.0.0

# Or revert migration
python3 scripts/migrate.py --target v1.0.0 --rollback
```

#### Data Compatibility

- v1.1.0 reads v1.0.0 data without modification
- v1.0.0 cannot write to v1.1.0 database (archived_at column)
- Recommend full v1.1.0 cutover within 24 hours

---

## Security Updates

### v1.0.1 (Patch Release) - Security Fix

**Issue**: Input validation bypass on clip URLs

**Severity**: Medium

**Fix**: Enhanced URL validation to prevent open redirects

**Upgrade**: Critical - Apply immediately

```bash
docker pull waddlebot-clip-interaction:v1.0.1
docker run ... waddlebot-clip-interaction:v1.0.1
```

---

## Changelog Archive

### v1.0.0

- Initial release
- All endpoints implemented
- Full documentation
- Test coverage 85%

---

## Support & Questions

For upgrade questions or version planning:

- **Issues**: GitHub Issues with label `clip-interaction-module`
- **Email**: support@penguintech.io
- **Slack**: #waddlebot-dev on Penguin Tech workspace

For feature requests:

- **RFC Process**: Submit detailed proposal in GitHub Discussions
- **Voting**: Community votes on proposed features
- **Priority**: High-voted features prioritized for next release
