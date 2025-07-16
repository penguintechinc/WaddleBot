// WaddleBot Premium Mobile App Theme
// Color palette: White, Yellow, Black

export const COLORS = {
  // Primary Colors
  PRIMARY: '#000000',        // Black
  SECONDARY: '#FFD700',      // Gold/Yellow
  BACKGROUND: '#FFFFFF',     // White
  
  // Text Colors
  TEXT_PRIMARY: '#000000',   // Black text
  TEXT_SECONDARY: '#666666', // Gray text
  TEXT_LIGHT: '#FFFFFF',     // White text
  TEXT_MUTED: '#999999',     // Muted gray
  
  // Accent Colors
  ACCENT_YELLOW: '#FFD700',  // Gold
  ACCENT_LIGHT_YELLOW: '#FFF4B8', // Light yellow
  ACCENT_DARK_YELLOW: '#FFB800',  // Darker yellow
  
  // Status Colors
  SUCCESS: '#4CAF50',
  WARNING: '#FF9800',
  ERROR: '#F44336',
  INFO: '#2196F3',
  
  // Reputation Colors
  REPUTATION_EXCELLENT: '#4CAF50',  // 750-850
  REPUTATION_GOOD: '#8BC34A',       // 650-749
  REPUTATION_FAIR: '#FFC107',       // 550-649
  REPUTATION_POOR: '#FF9800',       // 500-549
  REPUTATION_BANNED: '#F44336',     // 450-499
  
  // UI Colors
  BORDER: '#E0E0E0',
  CARD_BACKGROUND: '#FFFFFF',
  CARD_SHADOW: '#000000',
  OVERLAY: 'rgba(0, 0, 0, 0.5)',
  
  // Input Colors
  INPUT_BACKGROUND: '#F8F8F8',
  INPUT_BORDER: '#E0E0E0',
  INPUT_BORDER_FOCUS: '#FFD700',
  
  // Button Colors
  BUTTON_PRIMARY: '#000000',
  BUTTON_SECONDARY: '#FFD700',
  BUTTON_DISABLED: '#CCCCCC',
  
  // Tab Colors
  TAB_ACTIVE: '#FFD700',
  TAB_INACTIVE: '#666666',
  TAB_BACKGROUND: '#FFFFFF',
};

export const SIZES = {
  // Font sizes
  FONT_SMALL: 12,
  FONT_MEDIUM: 14,
  FONT_LARGE: 16,
  FONT_XLARGE: 18,
  FONT_TITLE: 20,
  FONT_HEADER: 24,
  FONT_HERO: 32,
  
  // Spacing
  SPACING_TINY: 4,
  SPACING_SMALL: 8,
  SPACING_MEDIUM: 16,
  SPACING_LARGE: 24,
  SPACING_XLARGE: 32,
  SPACING_XXLARGE: 48,
  
  // Component sizes
  BUTTON_HEIGHT: 48,
  INPUT_HEIGHT: 48,
  CARD_RADIUS: 12,
  BUTTON_RADIUS: 8,
  ICON_SIZE: 24,
  ICON_LARGE: 32,
  
  // Screen margins
  SCREEN_MARGIN: 16,
  SECTION_MARGIN: 24,
};

export const FONTS = {
  REGULAR: 'System',
  MEDIUM: 'System',
  BOLD: 'System',
  
  // Font weights
  WEIGHT_NORMAL: '400',
  WEIGHT_MEDIUM: '500',
  WEIGHT_BOLD: '700',
  WEIGHT_BLACK: '900',
};

export const SHADOWS = {
  LIGHT: {
    shadowColor: COLORS.CARD_SHADOW,
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  MEDIUM: {
    shadowColor: COLORS.CARD_SHADOW,
    shadowOffset: {
      width: 0,
      height: 4,
    },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  HEAVY: {
    shadowColor: COLORS.CARD_SHADOW,
    shadowOffset: {
      width: 0,
      height: 8,
    },
    shadowOpacity: 0.2,
    shadowRadius: 16,
    elevation: 8,
  },
};

export const GRADIENTS = {
  PRIMARY: ['#FFD700', '#FFB800'],
  DARK: ['#000000', '#333333'],
  LIGHT: ['#FFFFFF', '#F8F8F8'],
  ACCENT: ['#FFD700', '#FFF4B8'],
};

export default {
  COLORS,
  SIZES,
  FONTS,
  SHADOWS,
  GRADIENTS,
};