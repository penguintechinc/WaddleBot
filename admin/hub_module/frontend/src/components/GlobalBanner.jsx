import { useState, useEffect } from 'react';
import { publicApi } from '../services/api';

// Module-level cache so the banner is only fetched once per page load
// across layout re-mounts.
let bannerCache = null;

function parseBannerText(text, textColor) {
  // Split on [label](url) markdown links and render them as <a> tags
  const parts = [];
  const linkPattern = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
  let lastIndex = 0;
  let match;

  while ((match = linkPattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    parts.push(
      <a
        key={match.index}
        href={match[2]}
        target="_blank"
        rel="noopener noreferrer"
        style={{ color: textColor, fontWeight: 600, textDecoration: 'underline' }}
      >
        {match[1]}
      </a>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts;
}

function getTextHash(text) {
  // Simple djb2-style hash for the dismiss key
  let hash = 5381;
  for (let i = 0; i < text.length; i++) {
    hash = ((hash << 5) + hash) ^ text.charCodeAt(i);
  }
  return (hash >>> 0).toString(36);
}

export default function GlobalBanner() {
  const [banner, setBanner] = useState(bannerCache);
  const [dismissed, setDismissed] = useState(false);

  useEffect(() => {
    if (bannerCache) {
      setBanner(bannerCache);
      return;
    }
    publicApi.getBanner()
      .then(res => {
        bannerCache = res.data;
        setBanner(res.data);
      })
      .catch(() => {
        // Silently ignore — banner is non-critical
      });
  }, []);

  useEffect(() => {
    if (!banner?.text) return;
    const key = `banner_dismissed_${getTextHash(banner.text)}`;
    setDismissed(localStorage.getItem(key) === '1');
  }, [banner?.text]);

  if (!banner || !banner.enabled || !banner.text || dismissed) return null;

  const handleDismiss = () => {
    const key = `banner_dismissed_${getTextHash(banner.text)}`;
    localStorage.setItem(key, '1');
    setDismissed(true);
  };

  return (
    <div
      style={{ backgroundColor: banner.bgColor, color: banner.textColor }}
      className="w-full px-4 py-2 text-sm font-medium flex items-center justify-center gap-2 relative z-50"
    >
      <span className="text-center">
        {parseBannerText(banner.text, banner.textColor)}
      </span>
      <button
        onClick={handleDismiss}
        aria-label="Dismiss banner"
        style={{ color: banner.textColor, opacity: 0.7 }}
        className="absolute right-3 top-1/2 -translate-y-1/2 hover:opacity-100 transition-opacity text-lg leading-none"
      >
        ✕
      </button>
    </div>
  );
}
