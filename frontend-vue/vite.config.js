import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/analizeaza-build': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
      '/chat-architect': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true,
      },
      '/benchmark': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true,
      },
    }
  }
})