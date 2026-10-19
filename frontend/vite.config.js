import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
const backend = process.env.MAI_BACKEND_URL || 'http://127.0.0.1:8000'
export default defineConfig(({ command }) => ({
  plugins: [react()],
  define: { 'import.meta.env.VITE_LOCAL_API_ORIGIN': JSON.stringify(command === 'serve' ? backend : '') },
  server: {
    host: '127.0.0.1',
    proxy: { '/api': backend },
  },
}))
