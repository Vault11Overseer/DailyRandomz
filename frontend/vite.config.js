import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [react(), VitePWA({
    registerType: 'autoUpdate',
    includeAssets: ['favicon.svg', 'icon-192.png', 'icon-512.png'],
    manifest: {
      name: 'DailyRandomz', short_name: 'Randomz',
      description: 'A daily dose of unexpected. Discover random facts and keep your favorites.',
      theme_color: '#284b39', background_color: '#f7f8f2',
      display: 'standalone', start_url: '/', scope: '/',
      icons: [192, 512].map(size => ({ src: `/icon-${size}.png`, sizes: `${size}x${size}`, type: 'image/png', purpose: 'any maskable' })),
    },
    workbox: { navigateFallbackDenylist: [/^\/api\//], globPatterns: ['**/*.{js,css,html,png,svg,ico}'] },
  })],
  server: { port: 5173, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000' } },
  preview: { port: 4173, strictPort: true, proxy: { '/api': 'http://127.0.0.1:8000' } },
})
