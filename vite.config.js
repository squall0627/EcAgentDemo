import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/products': 'http://localhost:8000',
      '/agent': 'http://localhost:8000'
    }
  }
})