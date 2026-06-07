import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:5174',
        changeOrigin: false,
      },
    },
  },
  build: {
    target: 'es2022',
    outDir: 'dist',
    sourcemap: true,
  },
});
