import { defineConfig, devices } from '@playwright/test'

/**
 * Кроссбраузерные и адаптивные проверки.
 * Перед первым запуском: npm run test:e2e:install
 * Запуск: npm run test:e2e (сам соберёт проект и поднимет vite preview)
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: true,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://localhost:4173',
    locale: 'ru-RU',
    timezoneId: 'Asia/Yekaterinburg',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    // Десктоп: три движка (Blink — Chrome/Edge/Яндекс/Opera, Gecko — Firefox, WebKit — Safari)
    { name: 'desktop-chrome', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } } },
    { name: 'desktop-firefox', use: { ...devices['Desktop Firefox'], viewport: { width: 1280, height: 800 } } },
    { name: 'desktop-safari', use: { ...devices['Desktop Safari'], viewport: { width: 1366, height: 768 } } },
    { name: 'wide-chrome', use: { ...devices['Desktop Chrome'], viewport: { width: 2560, height: 1440 } } },
    // Планшеты
    { name: 'ipad', use: { ...devices['iPad (gen 7)'] } },
    { name: 'ipad-landscape', use: { ...devices['iPad (gen 7) landscape'] } },
    // Телефоны
    { name: 'iphone-se', use: { ...devices['iPhone SE'] } }, // 320px — самый узкий экран
    { name: 'iphone-13', use: { ...devices['iPhone 13'] } },
    { name: 'iphone-landscape', use: { ...devices['iPhone 13 landscape'] } },
    { name: 'android-chrome', use: { ...devices['Pixel 7'] } },
    { name: 'android-small', use: { ...devices['Galaxy S9+'] } },
    { name: 'mobile-firefox', use: { browserName: 'firefox', viewport: { width: 360, height: 740 } } },
  ],
  webServer: {
    command: 'npm run build && npx vite preview --port 4173 --strictPort',
    url: 'http://localhost:4173',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000,
  },
})
