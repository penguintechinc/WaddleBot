# Browser Source Core Module - Usage Guide

## Quick Start

```bash
cd core/browser_source_core_module
python app.py
```

Module starts on ports:
- REST API: 8027
- gRPC: 50050

## Setting Up OBS Browser Source

### Step 1: Get Overlay Key

Overlay keys are managed by administrators. Contact your Waddles admin or retrieve from:
```sql
SELECT overlay_key FROM community_overlay_tokens WHERE community_id = 123;
```

### Step 2: Add Browser Source in OBS

1. **Sources** → **+** → **Browser**
2. **Create New**: Name it "Waddles Overlay"
3. **Properties**:
   - URL: `http://localhost:8027/overlay/YOUR_64_CHAR_KEY`
   - Width: 1920
   - Height: 1080
   - FPS: 30
   - Check "Shutdown source when not visible"
   - Check "Refresh browser when scene becomes active"

### Step 3: Position in Scene

- Drag to cover full canvas
- Overlay will display all enabled sources

## Caption Overlay Setup

### Step 1: Add Caption Browser Source

1. **Sources** → **+** → **Browser**
2. **Create New**: Name it "Live Captions"
3. **Properties**:
   - URL: `http://localhost:8027/overlay/captions/YOUR_64_CHAR_KEY`
   - Width: 1920
   - Height: 200
   - FPS: 30

### Step 2: Position Captions

- Move to bottom of screen
- Adjust height as needed
- Captions will appear as users chat

## Testing Captions

### Send Test Caption

```bash
curl -X POST http://localhost:8027/api/v1/internal/captions \
  -H "Content-Type: application/json" \
  -H "X-Service-Key: your-service-key" \
  -d '{
    "community_id": 123,
    "platform": "twitch",
    "username": "TestUser",
    "original_message": "Hello world",
    "translated_message": "Hola mundo",
    "detected_language": "en",
    "target_language": "es",
    "confidence": 0.95
  }'
```

### WebSocket Test Client

```html
<!DOCTYPE html>
<html>
<head><title>Caption Test</title></head>
<body>
  <div id="captions"></div>
  <script>
    const ws = new WebSocket(
      'ws://localhost:8027/ws/captions/123?key=YOUR_KEY'
    );

    ws.onmessage = (event) => {
      const caption = JSON.parse(event.data);
      const div = document.getElementById('captions');
      div.innerHTML += `<p>${caption.username}: ${caption.translated}</p>`;
    };
  </script>
</body>
</html>
```

## Common Customizations

### Theme Customization

Themes are stored in `community_overlay_tokens.theme_config`:

```sql
UPDATE community_overlay_tokens
SET theme_config = '{
  "background": "rgba(0, 0, 0, 0.5)",
  "font_family": "Roboto, sans-serif",
  "font_size": "18px",
  "text_color": "#00ff00"
}'
WHERE community_id = 123;
```

### Enable/Disable Sources

```sql
UPDATE community_overlay_tokens
SET enabled_sources = ARRAY['captions', 'ticker']
WHERE community_id = 123;
```

## Monitoring

### Check Active Connections

```python
# In Python shell
from app import caption_connections
print(f"Communities: {len(caption_connections)}")
for cid, conns in caption_connections.items():
    print(f"  Community {cid}: {len(conns)} connections")
```

### View Recent Captions

```sql
SELECT * FROM caption_events
WHERE community_id = 123
ORDER BY created_at DESC
LIMIT 10;
```

### Access Logs

```sql
SELECT * FROM overlay_access_log
WHERE community_id = 123
ORDER BY created_at DESC
LIMIT 20;
```

## Troubleshooting

### Overlay Not Loading

1. Check overlay key is correct (64 hex chars)
2. Verify module is running: `curl http://localhost:8027/health`
3. Check access logs for errors
4. Try accessing URL in browser first

### Captions Not Appearing

1. Check WebSocket connection in browser console
2. Verify overlay key is valid
3. Send test caption (see above)
4. Check translation module is forwarding captions

### Connection Keeps Dropping

1. Check network stability
2. Verify firewall allows WebSocket
3. Enable "Refresh browser when scene becomes active" in OBS
4. Check server logs for errors
