import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/live-ais': { target: 'http://127.0.0.1:8000', ws: true },
      '/data': 'http://127.0.0.1:8000',
      '/earthquakes': 'http://127.0.0.1:8000',
      '/ocean': 'http://127.0.0.1:8000',
      '/ports': 'http://127.0.0.1:8000',
      '/system': 'http://127.0.0.1:8000',
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
  },
})
