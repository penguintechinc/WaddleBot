// WaddleBot Premium Mobile App Configuration

export const API_CONFIG = {
  BASE_URL: 'https://api.waddlebot.io',
  PORTAL_API_URL: 'https://api.waddlebot.io/community',
  ROUTER_API_URL: 'https://api.waddlebot.io/router',
  MARKETPLACE_API_URL: 'https://api.waddlebot.io/marketplace',
  TIMEOUT: 30000,
  RETRY_ATTEMPTS: 3,
  RETRY_DELAY: 1000,
};

export const APP_CONFIG = {
  APP_NAME: 'WaddleBot Premium',
  APP_VERSION: '1.0.0',
  COMPANY_NAME: 'WaddleBot',
  PREMIUM_REQUIRED: true,
  SUBSCRIPTION_CHECK_INTERVAL: 300000, // 5 minutes
  SESSION_TIMEOUT: 3600000, // 1 hour
  REFRESH_TOKEN_THRESHOLD: 300000, // 5 minutes
};

export const STORAGE_KEYS = {
  USER_TOKEN: 'waddlebot_user_token',
  REFRESH_TOKEN: 'waddlebot_refresh_token',
  USER_DATA: 'waddlebot_user_data',
  PREMIUM_STATUS: 'waddlebot_premium_status',
  SETTINGS: 'waddlebot_settings',
  COMMUNITIES: 'waddlebot_communities',
  LAST_SYNC: 'waddlebot_last_sync',
};

export const PERMISSIONS = {
  CAMERA: 'camera',
  PHOTO_LIBRARY: 'photo',
  NOTIFICATIONS: 'notification',
  LOCATION: 'location',
};

export const ENDPOINTS = {
  // Authentication
  LOGIN: '/auth/login',
  LOGOUT: '/auth/logout',
  REFRESH: '/auth/refresh',
  VERIFY_PREMIUM: '/auth/verify-premium',
  
  // User Management
  USER_PROFILE: '/user/profile',
  USER_COMMUNITIES: '/user/communities',
  USER_PERMISSIONS: '/user/permissions',
  
  // Community Management
  COMMUNITIES: '/communities',
  COMMUNITY_MEMBERS: '/communities/:id/members',
  COMMUNITY_MODULES: '/communities/:id/modules',
  COMMUNITY_STATS: '/communities/:id/stats',
  COMMUNITY_SETTINGS: '/communities/:id/settings',
  
  // Module Management
  MODULES: '/modules',
  MODULE_INSTALL: '/modules/install',
  MODULE_UNINSTALL: '/modules/uninstall',
  MODULE_TOGGLE: '/modules/toggle',
  
  // Currency Management
  CURRENCY_SETTINGS: '/communities/:id/currency',
  CURRENCY_BALANCE: '/communities/:id/members/:memberId/currency',
  CURRENCY_TRANSACTIONS: '/communities/:id/currency/transactions',
  CURRENCY_EARN: '/communities/:id/currency/earn',
  CURRENCY_SPEND: '/communities/:id/currency/spend',
  
  // Payment Integration
  PAYMENT_METHODS: '/payment/methods',
  PAYMENT_PROCESS: '/payment/process',
  PAYMENT_VERIFY: '/payment/verify',
  PAYMENT_HISTORY: '/payment/history',
  
  // Raffle & Giveaway System
  RAFFLES: '/communities/:id/raffles',
  RAFFLE_ENTRIES: '/communities/:id/raffles/:raffleId/entries',
  RAFFLE_WINNERS: '/communities/:id/raffles/:raffleId/winners',
  GIVEAWAYS: '/communities/:id/giveaways',
  GIVEAWAY_ENTRIES: '/communities/:id/giveaways/:giveawayId/entries',
  GIVEAWAY_WINNERS: '/communities/:id/giveaways/:giveawayId/winners',
  
  // Analytics
  ANALYTICS: '/analytics',
  USAGE_STATS: '/analytics/usage',
  PERFORMANCE: '/analytics/performance',
  
  // Health Check
  HEALTH: '/health',
  STATUS: '/status',
};

export const NOTIFICATION_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

export const SCREEN_NAMES = {
  // Auth Stack
  LOGIN: 'Login',
  PREMIUM_GATE: 'PremiumGate',
  
  // Main App
  DASHBOARD: 'Dashboard',
  COMMUNITIES: 'Communities',
  COMMUNITY_DETAIL: 'CommunityDetail',
  MEMBERS: 'Members',
  MEMBER_DETAIL: 'MemberDetail',
  MODULES: 'Modules',
  MODULE_DETAIL: 'ModuleDetail',
  ANALYTICS: 'Analytics',
  SETTINGS: 'Settings',
  PROFILE: 'Profile',
  
  // Currency & Payment
  CURRENCY_SETTINGS: 'CurrencySettings',
  CURRENCY_HISTORY: 'CurrencyHistory',
  PAYMENT_METHODS: 'PaymentMethods',
  PAYMENT_PROCESS: 'PaymentProcess',
  
  // Raffle & Giveaway
  RAFFLES: 'Raffles',
  RAFFLE_DETAIL: 'RaffleDetail',
  CREATE_RAFFLE: 'CreateRaffle',
  GIVEAWAYS: 'Giveaways',
  GIVEAWAY_DETAIL: 'GiveawayDetail',
  CREATE_GIVEAWAY: 'CreateGiveaway',
  
  // Modals
  ADD_MEMBER: 'AddMember',
  EDIT_MEMBER: 'EditMember',
  INSTALL_MODULE: 'InstallModule',
  COMMUNITY_SETTINGS: 'CommunitySettings',
};

export const ROLE_PERMISSIONS = {
  OWNER: ['read', 'write', 'admin', 'manage_members', 'manage_modules', 'ban_members', 'unban_members', 'edit_reputation', 'view_logs', 'manage_currency', 'manage_payments', 'create_raffles', 'create_giveaways'],
  ADMIN: ['read', 'write', 'manage_members', 'manage_modules', 'ban_members', 'unban_members', 'edit_reputation', 'view_logs', 'manage_currency', 'manage_payments', 'create_raffles', 'create_giveaways'],
  MODERATOR: ['read', 'write', 'manage_members', 'ban_members', 'create_raffles', 'create_giveaways'],
  MEMBER: ['read', 'participate_raffles', 'participate_giveaways'],
};

export const REPUTATION_CONFIG = {
  MIN_SCORE: 450,
  MAX_SCORE: 850,
  DEFAULT_SCORE: 650,
  BAN_SCORE: 450,
  MIN_AUTO_BAN_THRESHOLD: 451,
  MAX_AUTO_BAN_THRESHOLD: 850,
  DEFAULT_AUTO_BAN_THRESHOLD: 500,
};

export const ACTIVITY_TYPES = {
  MEMBER_JOIN: 'member_join',
  MEMBER_LEAVE: 'member_leave',
  MODULE_INSTALL: 'module_install',
  MODULE_UNINSTALL: 'module_uninstall',
  SETTING_CHANGE: 'setting_change',
  ROLE_CHANGE: 'role_change',
  CURRENCY_EARNED: 'currency_earned',
  CURRENCY_SPENT: 'currency_spent',
  RAFFLE_CREATED: 'raffle_created',
  RAFFLE_ENTRY: 'raffle_entry',
  RAFFLE_WINNER: 'raffle_winner',
  GIVEAWAY_CREATED: 'giveaway_created',
  GIVEAWAY_ENTRY: 'giveaway_entry',
  GIVEAWAY_WINNER: 'giveaway_winner',
};

export const CURRENCY_CONFIG = {
  DEFAULT_NAME: 'Credits',
  MIN_PRICE: 0.01,
  MAX_PRICE: 999.99,
  DEFAULT_CHAT_REWARD: 1,
  DEFAULT_EVENT_REWARD: 5,
  MIN_CHAT_REWARD: 0,
  MAX_CHAT_REWARD: 100,
  MIN_EVENT_REWARD: 0,
  MAX_EVENT_REWARD: 1000,
  INITIAL_BALANCE: 0,
  MAX_BALANCE: 1000000,
};

export const PAYMENT_CONFIG = {
  PAYPAL_CLIENT_ID: process.env.PAYPAL_CLIENT_ID || '',
  STRIPE_PUBLISHABLE_KEY: process.env.STRIPE_PUBLISHABLE_KEY || '',
  SUPPORTED_CURRENCIES: ['USD', 'EUR', 'GBP', 'CAD', 'AUD'],
  DEFAULT_CURRENCY: 'USD',
  MIN_TRANSACTION: 0.50,
  MAX_TRANSACTION: 10000.00,
};

export const RAFFLE_CONFIG = {
  MIN_COST: 1,
  MAX_COST: 10000,
  MIN_DURATION: 300, // 5 minutes
  MAX_DURATION: 604800, // 7 days
  DEFAULT_DURATION: 3600, // 1 hour
  MAX_ENTRIES_PER_USER: 100,
  MIN_ENTRIES_PER_USER: 1,
};

export const GIVEAWAY_CONFIG = {
  MIN_COST: 1,
  MAX_COST: 10000,
  MIN_DURATION: 300, // 5 minutes
  MAX_DURATION: 604800, // 7 days
  DEFAULT_DURATION: 3600, // 1 hour
  MAX_ENTRIES_PER_USER: 1,
  MIN_ENTRIES_PER_USER: 1,
};

export const CHART_COLORS = {
  PRIMARY: '#FFD700',
  SECONDARY: '#000000',
  ACCENT: '#FFF4B8',
  SUCCESS: '#4CAF50',
  WARNING: '#FF9800',
  ERROR: '#F44336',
  INFO: '#2196F3',
};

export default {
  API_CONFIG,
  APP_CONFIG,
  STORAGE_KEYS,
  PERMISSIONS,
  ENDPOINTS,
  NOTIFICATION_TYPES,
  SCREEN_NAMES,
  ROLE_PERMISSIONS,
  REPUTATION_CONFIG,
  ACTIVITY_TYPES,
  CURRENCY_CONFIG,
  PAYMENT_CONFIG,
  RAFFLE_CONFIG,
  GIVEAWAY_CONFIG,
  CHART_COLORS,
};