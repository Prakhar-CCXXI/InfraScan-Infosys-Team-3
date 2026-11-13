import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/images': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/uploads': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/predictions': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/inspections': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/assets': {
       target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/health': {
       target: 'http://backend:8000',
        changeOrigin: true,
      },
    },
  },
});
