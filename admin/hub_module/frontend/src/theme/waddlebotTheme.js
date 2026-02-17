/**
 * Centralized Waddles theme colors for FormModalBuilder.
 *
 * Usage:
 *   import { WADDLES_COLORS, WADDLES_GOLD_COLORS } from '@/theme/waddlebotTheme';
 *
 *   <FormModalBuilder themeMode="dark" colors={WADDLES_COLORS} ... />
 *
 * WADDLES_COLORS      — navy/sky primary buttons (most pages)
 * WADDLES_GOLD_COLORS — navy/gold primary buttons (superadmin pages)
 */

/** Standard Waddles dark theme — sky-blue primary buttons */
export const WADDLES_COLORS = {
  modalBackground: 'bg-navy-800',
  headerBackground: 'bg-navy-800',
  footerBackground: 'bg-navy-850',
  overlayBackground: 'bg-black bg-opacity-50',
  titleText: 'text-sky-100',
  labelText: 'text-sky-100',
  descriptionText: 'text-navy-400',
  errorText: 'text-red-400',
  buttonText: 'text-white',
  fieldBackground: 'bg-navy-700',
  fieldBorder: 'border-navy-600',
  fieldText: 'text-sky-100',
  fieldPlaceholder: 'placeholder-navy-400',
  focusRing: 'focus:ring-gold-500',
  focusBorder: 'focus:border-gold-500',
  primaryButton: 'bg-sky-600',
  primaryButtonHover: 'hover:bg-sky-700',
  secondaryButton: 'bg-navy-700',
  secondaryButtonHover: 'hover:bg-navy-600',
  secondaryButtonBorder: 'border-navy-600',
  activeTab: 'text-gold-400',
  activeTabBorder: 'border-gold-500',
  inactiveTab: 'text-navy-400',
  inactiveTabHover: 'hover:text-navy-300 hover:border-navy-500',
  tabBorder: 'border-navy-700',
  errorTabText: 'text-red-400',
  errorTabBorder: 'border-red-500',
};

/** Gold-accent variant — gold primary buttons for superadmin panels */
export const WADDLES_GOLD_COLORS = {
  ...WADDLES_COLORS,
  modalBackground: 'bg-navy-900',
  headerBackground: 'bg-navy-900',
  footerBackground: 'bg-navy-900',
  titleText: 'text-gold-400',
  labelText: 'text-navy-300',
  buttonText: 'text-navy-950',
  fieldBackground: 'bg-navy-800',
  fieldBorder: 'border-navy-700',
  primaryButton: 'bg-gold-500',
  primaryButtonHover: 'hover:bg-gold-600',
  secondaryButtonBorder: 'border-navy-700',
  inactiveTabHover: 'hover:text-navy-300',
};
