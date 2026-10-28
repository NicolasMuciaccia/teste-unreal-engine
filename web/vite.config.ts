import { defineConfig } from 'vite';

// base relativa: o site funciona em qualquer subpasta (GitHub Pages, Cloudflare, etc.)
export default defineConfig({
  base: './',
  build: { target: 'es2020', chunkSizeWarningLimit: 1200 },
});
