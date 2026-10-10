import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import type { Plugin } from 'vite';

/** Explicit development-only downloads; never exposes arbitrary workspace files. */
export function journalDownloadsPlugin(): Plugin {
  const downloads = new Map([
    ['journal-images-oct08-dec31-2026.pdf', {
      file: path.resolve(import.meta.dirname, '../../generated-artifacts/journal-images-oct08-dec31-2026.pdf'),
      contentType: 'application/pdf',
    }],
    ['aleksandra-welcome.mp3', {
      file: path.resolve(import.meta.dirname, '../../website/elh-preview/assets/audio/aleksandra-welcome.mp3'),
      contentType: 'audio/mpeg',
    }],
  ]);
  return {
    name: 'journal-image-download',
    apply: 'serve',
    configureServer(server) {
      const prefix = `${server.config.base}downloads/`;
      server.middlewares.use(async (request, response, next) => {
        const pathname = new URL(request.url || '/', 'http://preview.invalid').pathname;
        if (!pathname.startsWith(prefix)) return next();
        const filename = pathname.slice(prefix.length);
        const download = downloads.get(filename);
        if (!download) return next();
        response.setHeader('Cache-Control', 'no-store');
        response.setHeader('X-Robots-Tag', 'noindex, noarchive');
        response.setHeader('X-Content-Type-Options', 'nosniff');
        if (request.method !== 'GET' && request.method !== 'HEAD') {
          response.statusCode = 405;
          response.setHeader('Allow', 'GET, HEAD');
          response.end('Method not allowed');
          return;
        }
        try {
          const metadata = await stat(download.file);
          if (!metadata.isFile()) throw new Error('Export is not a file');
          response.statusCode = 200;
          response.setHeader('Content-Type', download.contentType);
          response.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
          response.setHeader('Content-Length', metadata.size);
          if (request.method === 'HEAD') {
            response.end();
            return;
          }
          const stream = createReadStream(download.file);
          stream.on('error', (error) => {
            server.config.logger.error(`Asset download failed: ${error.message}`);
            response.destroy(error);
          });
          response.on('close', () => stream.destroy());
          stream.pipe(response);
        } catch (error) {
          const missing = (error as NodeJS.ErrnoException).code === 'ENOENT';
          response.statusCode = missing ? 404 : 500;
          response.end(missing ? 'Download is not available.' : 'Asset download failed.');
          if (!missing) server.config.logger.error(String(error));
        }
      });
    },
  };
}
