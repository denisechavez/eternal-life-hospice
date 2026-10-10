import path from 'path';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

import runtimeErrorOverlay from '@replit/vite-plugin-runtime-error-modal';
import { mockupPreviewPlugin } from './mockupPreviewPlugin';
import { liveReportingPlugin } from './liveReportingPlugin';
import { brevoReportingPlugin } from './brevoReportingPlugin';
import { whatConvertsReportingPlugin } from './whatConvertsReportingPlugin';
import { journalDownloadsPlugin } from './journalDownloadsPlugin';

const rawPort = process.env.PORT;

if (!rawPort) {
  throw new Error(
    'PORT environment variable is required but was not provided.',
  );
}

const port = Number(rawPort);

if (Number.isNaN(port) || port <= 0) {
  throw new Error(`Invalid PORT value: "${rawPort}"`);
}

const basePath = process.env.BASE_PATH;

if (!basePath) {
  throw new Error(
    'BASE_PATH environment variable is required but was not provided.',
  );
}

export default defineConfig({
  base: basePath,
  plugins: [
    journalDownloadsPlugin(),
    liveReportingPlugin(),
    brevoReportingPlugin(),
    whatConvertsReportingPlugin(),
    mockupPreviewPlugin(),
    react(),
    tailwindcss(),
    runtimeErrorOverlay(),
    ...(process.env.NODE_ENV !== 'production' &&
    process.env.REPL_ID !== undefined
      ? [
          await import('@replit/vite-plugin-cartographer').then((m) =>
            m.cartographer({
              root: path.resolve(import.meta.dirname, '..'),
            }),
          ),
        ]
      : []),
  ],
  resolve: {
    // The shared Clerk package lives above this artifact. Resolve its React
    // peers to this app's runtime, not a second parent-level React instance.
    dedupe: ['react', 'react-dom'],
    alias: {
      '@': path.resolve(import.meta.dirname, 'src'),
    },
  },
  root: path.resolve(import.meta.dirname),
  build: {
    outDir: path.resolve(import.meta.dirname, 'dist'),
    emptyOutDir: true,
  },
  server: {
    port,
    strictPort: true,
    host: '0.0.0.0',
    allowedHosts: true,
    // Article srcdoc uses the site's original /assets paths. Serve those from
    // the existing website service, including when previewing this port alone.
    proxy: {
      '/api/studio': {
        target: 'http://127.0.0.1:5000',
      },
      '/api/journal-release-status': {
        target: 'http://127.0.0.1:5000',
      },
      '/api/journal-photo': {
        target: 'http://127.0.0.1:5000',
      },
      '/assets': {
        target: 'http://127.0.0.1:5000',
      },
    },
    fs: {
      strict: true,
    },
  },
  preview: {
    port,
    host: '0.0.0.0',
    allowedHosts: true,
  },
});
