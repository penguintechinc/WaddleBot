/**
 * Shared platform configuration - single source of truth for all platform
 * icons, colors, labels, and badge styles across the Waddles frontend.
 */

const platformConfig = {
  discord: {
    icon: '\uD83D\uDCAC',
    label: 'Discord',
    color: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
    hex: '#5865F2',
  },
  twitch: {
    icon: '\uD83D\uDCFA',
    label: 'Twitch',
    color: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
    hex: '#9146FF',
  },
  slack: {
    icon: '\uD83D\uDCBC',
    label: 'Slack',
    color: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    hex: '#36C5F0',
  },
  youtube: {
    icon: '\u25B6\uFE0F',
    label: 'YouTube',
    color: 'bg-red-500/20 text-red-300 border-red-500/30',
    hex: '#FF0000',
  },
  kick: {
    icon: '\uD83D\uDFE2',
    label: 'KICK',
    color: 'bg-green-500/20 text-green-300 border-green-500/30',
    hex: '#53FC18',
  },
  telegram: {
    icon: '\u2708\uFE0F',
    label: 'Telegram',
    color: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
    hex: '#26A5E4',
  },
  matrix: {
    icon: '\u2B1B',
    label: 'Matrix',
    color: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
    hex: '#0DBD8B',
  },
  guilded: {
    icon: '\uD83C\uDFC6',
    label: 'Guilded',
    color: 'bg-gold-500/20 text-gold-300 border-gold-500/30',
    hex: '#F5C400',
  },
  revolt: {
    icon: '\uD83D\uDD34',
    label: 'Revolt',
    color: 'bg-red-500/20 text-red-300 border-red-500/30',
    hex: '#FF4654',
  },
  hub: {
    icon: '\uD83D\uDC27',
    label: 'Hub Chat',
    color: 'bg-sky-500/20 text-sky-300 border-sky-500/30',
    hex: '#38BDF8',
  },
};

const defaultPlatform = {
  icon: '\uD83C\uDF10',
  label: 'Unknown',
  color: 'bg-navy-700 text-navy-300 border-navy-600',
  hex: '#94A3B8',
};

/**
 * Get the emoji icon for a platform.
 * @param {string} platform - Platform key (e.g. 'discord', 'twitch')
 * @returns {string} Emoji icon
 */
export function getPlatformIcon(platform) {
  return (platformConfig[platform] || defaultPlatform).icon;
}

/**
 * Get the Tailwind color/badge class string for a platform.
 * @param {string} platform - Platform key
 * @returns {string} Tailwind CSS classes
 */
export function getPlatformColor(platform) {
  return (platformConfig[platform] || defaultPlatform).color;
}

/**
 * Get the display label for a platform.
 * @param {string} platform - Platform key
 * @returns {string} Human-readable label
 */
export function getPlatformLabel(platform) {
  return (platformConfig[platform] || defaultPlatform).label;
}

/**
 * Get the full config object for a platform (icon, label, color, hex).
 * Falls back to defaultPlatform for unknown keys.
 * @param {string} platform - Platform key
 * @returns {{ icon: string, label: string, color: string, hex: string }}
 */
export function getPlatformConfig(platform) {
  return platformConfig[platform] || defaultPlatform;
}

/**
 * Get all supported platform keys.
 * @returns {string[]}
 */
export function getAllPlatforms() {
  return Object.keys(platformConfig);
}

/**
 * Get all platforms as an array of { id, icon, label, color, hex } objects.
 * Useful for rendering filter dropdowns and selection grids.
 * @returns {Array<{ id: string, icon: string, label: string, color: string, hex: string }>}
 */
export function getAllPlatformOptions() {
  return Object.entries(platformConfig).map(([id, cfg]) => ({ id, ...cfg }));
}

export { platformConfig, defaultPlatform };
