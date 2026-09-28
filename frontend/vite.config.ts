/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath } from 'node:url';

const designDir = fileURLToPath(new URL('../design', import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@design': designDir },
  },
  server: {
    port: 5173,
    // tokens.css is imported straight from ../design so there is one source of truth.
    fs: { allow: ['.', designDir] },
    // When VITE_USE_FIXTURES=false, /api goes to the FastAPI backend (LENS_API_URL if 8000 is taken).
    proxy: { '/api': process.env.LENS_API_URL ?? 'http://localhost:8000' },
  },
  test: {
    environment: 'node',
  },
});
