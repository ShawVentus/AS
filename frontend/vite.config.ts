import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // 监听所有网络接口，允许外部访问
    allowedHosts: true,
    port: parseInt(process.env.VITE_PORT || '5173'),
    hmr: false,  // 禁用热更新，避免 Bohrium 容器环境下 WebSocket 连接失败
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
