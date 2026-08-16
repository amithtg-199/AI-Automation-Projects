import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
// If running Vite on Windows but backend is in WSL2, set VITE_BACKEND_URL env var:
//   VITE_BACKEND_URL=http://172.28.x.x:8000 npm run dev
// Otherwise localhost:8000 works when both run inside WSL2.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_BACKEND_URL || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
