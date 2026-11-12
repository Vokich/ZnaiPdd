import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

export default defineConfig(() => {
  const backend = process.env.DJANGO_PROXY_TARGET ?? 'http://127.0.0.1:8000'
  const proxy = { target: backend }
  return {
    plugins: [react()],
    server: {
      proxy: Object.fromEntries(
        ['/api', '/admin', '/static', '/media', '/download-training/', '/certificate/']
          .map(path => [path, proxy]),
      ),
    },
  }
})
