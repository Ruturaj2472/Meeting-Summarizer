import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/meetings': 'http://localhost:8000',
      '/action-items': 'http://localhost:8000',
    }
  },
  build: {
    outDir: 'dist'
  }
})