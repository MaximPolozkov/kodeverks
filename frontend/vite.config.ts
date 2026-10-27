/// <reference types="vitest" />
import { fileURLToPath, URL } from 'node:url'

import legacy from '@vitejs/plugin-legacy'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

/**
 * Поддерживаемые браузеры (совпадают с "browserslist" в package.json):
 * Chrome/Яндекс.Браузер/Opera/Samsung Internet на Chromium 87+, Edge 88+,
 * Firefox 78+, Safari 14.1+ (macOS и iOS 14.5+).
 * Нижняя граница Safari 14.1 — первая версия с flex gap, которую нельзя заполифиллить.
 */
const BROWSER_TARGETS = ['chrome87', 'edge88', 'firefox78', 'safari14', 'ios14', 'opera73']

export default defineConfig({
  plugins: [
    react(),
    // Полифилы недостающих в старых браузерах функций (по факту использования в коде).
    // Отдельные legacy-чанки не нужны: все целевые браузеры поддерживают ES-модули.
    legacy({
      modernTargets: 'chrome>=87, edge>=88, firefox>=78, safari>=14.1, ios>=14.5, opera>=73, samsung>=14',
      modernPolyfills: true,
      renderLegacyChunks: false,
    }),
  ],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  build: {
    // Синтаксис JS понижает plugin-legacy по modernTargets (он же задаёт build.target).
    // CSS понижаем отдельно: например, inset → top/right/bottom/left для старого Safari
    cssTarget: BROWSER_TARGETS,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
})
