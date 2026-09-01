"""Server-side HTML renderers for every OBS browser-source surface.

Vanilla HTML+JS, no build step, no heavy framework (task requirement) --
every surface embeds a small inline `<script>` that opens a real
`EventSource` against this same service's `/overlay/<community>/<surface>/
live` SSE route (`services/presentation_hub.py`) for live push updates.
Community/surface path segments are `html.escape()`d wherever reflected
(security.md Input Validation: escape outputs) -- the surfaces this module
renders are otherwise open (no per-community overlay-key auth wired yet,
matching this scaffold's pre-existing, explicitly-documented posture; see
`docs/plans/2026-08-31-music-station-design.md` §11.9, still an open
decision, not silently skipped).
"""

from __future__ import annotations

import html
import json
from typing import Any

#: Shared dark-glass styling, close to
#: `core/browser_source_core_module/templates/music-player-overlay.html`'s
#: existing look so the Music Station reads as a sibling of the legacy
#: overlay it supersedes, not a visual break.
_BASE_STYLE = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: var(--wb-font, 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif);
      background: transparent; overflow: hidden; color: #fff; }
    .hidden { display: none !important; }
"""


def _theme_style(
    *,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    font_family: str | None = None,
) -> str:
    """Build a `:root{...}` CSS-variable block from `presentation_config` overrides.

    Real per-community theming, not decoration: `services/render.py`'s
    callers pull these three fields from
    `services/presentation_config_service.get_theme_config()` (backed by
    the `presentation_config` table, migration 073) and every surface
    below consumes them via `var(--wb-primary, <default>)` -- an unset
    field falls through to the same default it always had.
    """
    primary = html.escape(primary_color) if primary_color else "#1db954"
    secondary = html.escape(secondary_color) if secondary_color else "#1ed760"
    default_font = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif"
    font = html.escape(font_family) if font_family else default_font
    return f"""
    <style>
      :root {{
        --wb-primary: {primary};
        --wb-secondary: {secondary};
        --wb-font: {font};
      }}
    </style>
    """


def _sse_bootstrap_script(community: str, surface: str, on_message_body: str) -> str:
    """Build the `<script>` block every surface uses to open its live SSE connection.

    `on_message_body` is raw, trusted JS (authored in this file only, never
    from a request) injected into the `EventSource.onmessage` handler body.
    """
    safe_community = json.dumps(community)
    safe_surface = json.dumps(surface)
    return f"""
    <script>
      const community = {safe_community};
      const surface = {safe_surface};
      const source = new EventSource(`/overlay/${{community}}/${{surface}}/live`);
      source.onmessage = (event) => {{
        const data = JSON.parse(event.data);
        {on_message_body}
      }};
      source.onerror = (err) => {{
        console.error('presentation live connection error', err);
      }};
    </script>
    """


def render_full_screen(
    community: str,
    surface: str,
    *,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    font_family: str | None = None,
) -> str:
    """Full-bleed overlay surface -- pushed content replaces the entire visible area."""
    safe_community = html.escape(community)
    safe_surface = html.escape(surface)
    theme_style = _theme_style(
        primary_color=primary_color, secondary_color=secondary_color, font_family=font_family
    )
    on_message = """
        if (!data || data.type === 'clear') {
          document.getElementById('content').classList.add('hidden');
          return;
        }
        const el = document.getElementById('content');
        el.classList.remove('hidden');
        document.getElementById('title').textContent = data.title || '';
        document.getElementById('body').textContent = data.body || '';
        const img = document.getElementById('image');
        if (data.image_url && /^https?:\\/\\//.test(data.image_url)) {
          img.src = data.image_url;
          img.classList.remove('hidden');
        } else {
          img.classList.add('hidden');
          img.removeAttribute('src');
        }
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>svc-presentation -- full_screen -- {safe_community}</title>
{theme_style}
<style>
{_BASE_STYLE}
    #content {{ position: fixed; inset: 0; display: flex; flex-direction: column;
      align-items: center; justify-content: center; text-align: center; padding: 40px; }}
    #image {{ max-width: 80%; max-height: 60%; border-radius: 12px; margin-bottom: 24px; }}
    #title {{ font-size: 48px; font-weight: bold; color: var(--wb-primary, #fff);
      text-shadow: 0 2px 8px rgba(0,0,0,0.7); }}
    #body {{ font-size: 24px; margin-top: 12px; text-shadow: 0 1px 4px rgba(0,0,0,0.7); }}
</style>
</head>
<body data-community="{safe_community}" data-surface="{safe_surface}">
  <div id="content" class="hidden">
    <img id="image" class="hidden" alt="">
    <div id="title"></div>
    <div id="body"></div>
  </div>
  {_sse_bootstrap_script(community, surface, on_message)}
</body>
</html>"""


def render_media(
    community: str,
    surface: str,
    *,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    font_family: str | None = None,
) -> str:
    """Media / lower-third overlay surface -- bottom-left card, pushed content updates it."""
    safe_community = html.escape(community)
    safe_surface = html.escape(surface)
    theme_style = _theme_style(
        primary_color=primary_color, secondary_color=secondary_color, font_family=font_family
    )
    on_message = """
        const card = document.getElementById('card');
        if (!data || data.type === 'clear') {
          card.classList.add('hidden');
          return;
        }
        card.classList.remove('hidden');
        document.getElementById('title').textContent = data.title || '';
        document.getElementById('body').textContent = data.body || '';
        const img = document.getElementById('image');
        if (data.image_url && /^https?:\\/\\//.test(data.image_url)) {
          img.src = data.image_url;
          img.classList.remove('hidden');
        } else {
          img.classList.add('hidden');
          img.removeAttribute('src');
        }
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>svc-presentation -- media -- {safe_community}</title>
{theme_style}
<style>
{_BASE_STYLE}
    #card {{ position: fixed; bottom: 24px; left: 24px; max-width: 480px;
      background: linear-gradient(135deg, rgba(0,0,0,0.85), rgba(20,20,20,0.85));
      border-radius: 14px; padding: 18px 22px; backdrop-filter: blur(10px);
      box-shadow: 0 8px 32px rgba(0,0,0,0.5); display: flex; gap: 14px; align-items: center; }}
    #image {{ width: 72px; height: 72px; border-radius: 8px; object-fit: cover; }}
    #title {{ font-size: 20px; font-weight: bold; color: var(--wb-primary, #fff); }}
    #body {{ font-size: 15px; color: #ccc; margin-top: 4px; }}
</style>
</head>
<body data-community="{safe_community}" data-surface="{safe_surface}">
  <div id="card" class="hidden">
    <img id="image" class="hidden" alt="">
    <div>
      <div id="title"></div>
      <div id="body"></div>
    </div>
  </div>
  {_sse_bootstrap_script(community, surface, on_message)}
</body>
</html>"""


def render_crawler(
    community: str,
    surface: str,
    *,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    font_family: str | None = None,
) -> str:
    """Bottom-screen scrolling ticker surface -- pushed text scrolls right-to-left."""
    safe_community = html.escape(community)
    safe_surface = html.escape(surface)
    theme_style = _theme_style(
        primary_color=primary_color, secondary_color=secondary_color, font_family=font_family
    )
    on_message = """
        const track = document.getElementById('track');
        track.textContent = (data && data.text) ? data.text : '';
        track.classList.toggle('hidden', !track.textContent);
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>svc-presentation -- crawler -- {safe_community}</title>
{theme_style}
<style>
{_BASE_STYLE}
    #ticker {{ position: fixed; bottom: 0; left: 0; right: 0; height: 56px;
      background: rgba(0,0,0,0.75); display: flex; align-items: center; overflow: hidden; }}
    #track {{ white-space: nowrap; font-size: 26px; font-weight: 600;
      color: var(--wb-primary, #fff);
      padding-left: 100%; animation: scroll-left 20s linear infinite; }}
    @keyframes scroll-left {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(-100%); }}
    }}
</style>
</head>
<body data-community="{safe_community}" data-surface="{safe_surface}">
  <div id="ticker">
    <div id="track" class="hidden"></div>
  </div>
  {_sse_bootstrap_script(community, surface, on_message)}
</body>
</html>"""


def render_music(
    community: str,
    *,
    primary_color: str | None = None,
    secondary_color: str | None = None,
    font_family: str | None = None,
) -> str:
    """Music Station browser-source player -- now-playing + upcoming queue, polling `/queue`.

    Embeds the YouTube IFrame API player for `provider == "youtube"` tracks
    and a Spotify track embed for `provider == "spotify"` tracks (task
    scope). Other providers (e.g. SoundCloud) still render in the
    now-playing/queue list, honestly without a player embed.
    """
    safe_community = html.escape(community)
    theme_style = _theme_style(
        primary_color=primary_color, secondary_color=secondary_color, font_family=font_family
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>svc-presentation -- music -- {safe_community}</title>
{theme_style}
<style>
{_BASE_STYLE}
    #station {{ position: fixed; bottom: 20px; right: 20px; width: 420px;
      background: linear-gradient(135deg, rgba(0,0,0,0.88), rgba(20,20,20,0.88));
      border-radius: 16px; padding: 20px; backdrop-filter: blur(10px);
      box-shadow: 0 8px 32px rgba(0,0,0,0.5); }}
    #player-slot {{ width: 100%; height: 200px; border-radius: 10px; margin-bottom: 14px;
      background: #111; overflow: hidden; }}
    #player-slot iframe {{ width: 100%; height: 100%; border: 0; }}
    #now-playing .title {{ font-size: 19px; font-weight: bold; }}
    #now-playing .artist {{ font-size: 15px; color: #ccc; margin-top: 2px; }}
    #progress-bar {{ width: 100%; height: 4px; background: rgba(255,255,255,0.2);
      border-radius: 2px; margin-top: 12px; overflow: hidden; }}
    #progress-fill {{ height: 100%; width: 0%;
      background: linear-gradient(90deg, var(--wb-primary, #1db954), var(--wb-secondary, #1ed760));
      transition: width 0.25s linear; }}
    #up-next {{ margin-top: 16px; font-size: 13px; color: #aaa; }}
    #up-next-list {{ list-style: none; margin-top: 6px; max-height: 120px; overflow-y: auto; }}
    #up-next-list li {{ padding: 4px 0; border-top: 1px solid rgba(255,255,255,0.08); }}
    #empty-state {{ font-size: 14px; color: #999; text-align: center; padding: 20px 0; }}
</style>
</head>
<body data-community="{safe_community}" data-surface="music">
  <div id="station">
    <div id="player-slot"></div>
    <div id="now-playing" class="hidden">
      <div class="title" id="np-title"></div>
      <div class="artist" id="np-artist"></div>
      <div id="progress-bar"><div id="progress-fill"></div></div>
    </div>
    <div id="empty-state">No tracks queued</div>
    <div id="up-next">
      Up next
      <ul id="up-next-list"></ul>
    </div>
  </div>
  <!-- No Subresource Integrity attribute: YouTube serves this file dynamically
       and does not publish a stable hash to pin against (same accepted
       exception every YouTube-embedding site relies on) -- first-party
       Google domain, loaded over HTTPS. -->
  <script src="https://www.youtube.com/iframe_api"></script>
  <script>
    const community = {json.dumps(community)};
    const POLL_INTERVAL_MS = 5000;
    let currentQueueId = null;
    let trackStartedAtMs = null;
    let currentDurationMs = 0;
    let ytPlayer = null;
    let ytReady = false;

    window.onYouTubeIframeAPIReady = () => {{ ytReady = true; }};

    function renderPlayer(track) {{
      const slot = document.getElementById('player-slot');
      if (track.provider === 'spotify' && track.external_id) {{
        const trackId = encodeURIComponent(track.external_id);
        const src = `https://open.spotify.com/embed/track/${{trackId}}`;
        slot.innerHTML = `<iframe src="${{src}}" allow="encrypted-media" loading="lazy"></iframe>`;
        ytPlayer = null;
      }} else if (track.provider === 'youtube' && track.external_id) {{
        slot.innerHTML = '<div id="yt-target"></div>';
        if (ytReady && window.YT) {{
          ytPlayer = new YT.Player('yt-target', {{
            videoId: track.external_id,
            playerVars: {{ autoplay: 1, controls: 0, modestbranding: 1 }},
          }});
        }}
      }} else {{
        const label = track.provider ? track.provider + ' (no embeddable player)' : '';
        slot.innerHTML =
          '<div style="display:flex;align-items:center;justify-content:center;' +
          'height:100%;color:#888;">' + label + '</div>';
        ytPlayer = null;
      }}
    }}

    function renderQueue(payload) {{
      const nowPlaying = payload.now_playing;
      const upcoming = payload.upcoming || [];
      const npEl = document.getElementById('now-playing');
      const emptyEl = document.getElementById('empty-state');

      if (!nowPlaying) {{
        npEl.classList.add('hidden');
        emptyEl.classList.remove('hidden');
        document.getElementById('player-slot').innerHTML = '';
        currentQueueId = null;
      }} else {{
        emptyEl.classList.add('hidden');
        npEl.classList.remove('hidden');
        document.getElementById('np-title').textContent = nowPlaying.name;
        document.getElementById('np-artist').textContent = nowPlaying.artist;

        if (nowPlaying.queue_id !== currentQueueId) {{
          currentQueueId = nowPlaying.queue_id;
          trackStartedAtMs = Date.now();
          currentDurationMs = nowPlaying.duration_ms || 0;
          renderPlayer(nowPlaying);
        }}
      }}

      const list = document.getElementById('up-next-list');
      list.innerHTML = '';
      for (const track of upcoming) {{
        const li = document.createElement('li');
        li.textContent = `${{track.name}} -- ${{track.artist}}`;
        list.appendChild(li);
      }}
    }}

    async function pollQueue() {{
      try {{
        const resp = await fetch(`/overlay/${{community}}/music/queue`);
        if (!resp.ok) return;
        const payload = await resp.json();
        renderQueue(payload);
      }} catch (err) {{
        console.error('music queue poll failed', err);
      }}
    }}

    setInterval(() => {{
      if (!currentQueueId || !trackStartedAtMs || !currentDurationMs) return;
      const elapsed = Date.now() - trackStartedAtMs;
      const pct = Math.min(100, (elapsed / currentDurationMs) * 100);
      document.getElementById('progress-fill').style.width = pct + '%';
    }}, 250);

    pollQueue();
    setInterval(pollQueue, POLL_INTERVAL_MS);
  </script>
</body>
</html>"""


RENDERERS: dict[str, Any] = {
    "full_screen": render_full_screen,
    "media": render_media,
    "crawler": render_crawler,
}
