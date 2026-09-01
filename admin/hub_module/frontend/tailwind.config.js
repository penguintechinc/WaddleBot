/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Navy - Primary dark backgrounds
        navy: {
          50: '#f0f4f8',
          100: '#d9e2ec',
          200: '#bcccdc',
          300: '#9fb3c8',
          400: '#829ab1',
          500: '#627d98',
          600: '#486581',
          700: '#334e68',
          800: '#243b53',
          900: '#102a43',
          950: '#0a1929',
        },
        // Light Blue - Accents and interactive elements
        sky: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Gold - Highlights, CTAs, and important elements
        gold: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        // Green - Success states and positive actions
        emerald: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        // Waddles brand colors
        waddle: {
          navy: '#102a43',
          lightBlue: '#38bdf8',
          gold: '#fbbf24',
          green: '#10b981',
          dark: '#0a1929',
          light: '#e0f2fe',
        },
      },
      backgroundColor: {
        dark: '#0a1929',
        'dark-card': '#102a43',
        'dark-hover': '#243b53',
      },
      textColor: {
        'dark-primary': '#e0f2fe',
        'dark-secondary': '#9fb3c8',
        'dark-muted': '#627d98',
      },
      borderColor: {
        'dark-border': '#334e68',
      },
    },
  },
  plugins: [],
};
