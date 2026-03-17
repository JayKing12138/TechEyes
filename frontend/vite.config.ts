import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const backendTarget = process.env.VITE_BACKEND_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        // Default to backend on 8000; override with VITE_BACKEND_TARGET when needed.
        target: backendTarget,
        changeOrigin: true,
      },
    },
  },
})
