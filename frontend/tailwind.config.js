/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  future: {
    // hover-стили только на устройствах с мышью: на телефонах кнопки не «залипают» после тапа
    hoverOnlyWhenSupported: true,
  },
  theme: {
    extend: {
      screens: {
        // Узкие телефоны (iPhone SE, 320–399px) получают отдельную раскладку
        xs: '400px',
      },
      colors: {
        paper: '#F2F4F6',
        ink: { DEFAULT: '#15202B', soft: '#2B3846' },
        muted: '#5B6877',
        line: '#D3DAE2',
        cobalt: { DEFAULT: '#2246D6', dark: '#1A37AC', tint: '#E6ECFC' },
        marker: { DEFAULT: '#F3C34A', tint: '#FDF3D6' },
        danger: '#B83A26',
        ok: '#2C7A4B',
      },
      fontFamily: {
        display: ['Unbounded', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        sans: ['Onest', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      },
      maxWidth: { page: '76rem' },
    },
  },
  plugins: [],
}
