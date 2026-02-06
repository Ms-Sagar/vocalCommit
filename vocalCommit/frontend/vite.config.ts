import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: parseInt(process.env.PORT || '5173'),
    allowedHosts: [
      'vocalcommit-admin.onrender.com',
      'vocalcommit-frontend.onrender.com',
      'localhost',
      '127.0.0.1'
    ],
  },
  preview: {
    host: '0.0.0.0',
    port: parseInt(process.env.PORT || '4173'),
    allowedHosts: [
      'vocalcommit-admin.onrender.com',
      'vocalcommit-frontend.onrender.com',
      'localhost',
      '127.0.0.1'
    ],
  },
})
