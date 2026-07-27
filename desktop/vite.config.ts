import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite config for Tauri desktop app
// Frontend is built separately and symlinked; this is a minimal shell config
export default defineConfig({
  plugins: [react()],
  server: {
    // dev server for Tauri frontend
    port: 5173,
    strictPort: true,
    cors: true,
  },
  build: {
    outDir: 'dist',
    minify: 'terser',
    sourcemap: false,
  },
});
