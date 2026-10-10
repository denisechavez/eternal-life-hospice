import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import path from 'node:path';
import type { Plugin } from 'vite';

/** One explicit development-only download; never exposes arbitrary workspace files. */
export function journalDownloadsPlugin(): Plugin {
  const filename = 'journal-images-oct08-dec31-2026.pdf';
  const file = path.resolve(import.meta.dirname, '../../generated-artifacts', filename);
  return {
    name: 'journal-image-download',
    apply: 'serve',
    configureServer(server) {
      const route = `${server.config.base}downloads/${filename}`;
      server.middlewares.use(async (request, response, next) => {
        const pathname = new URL(request.url || '/', 'http://preview.invalid').pathname;
        if (pathname !== route) return next();
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
          const metadata = await stat(file);
          if (!metadata.isFile()) throw new Error('Export is not a file');
          response.statusCode = 200;
          response.setHeader('Content-Type', 'application/pdf');
          response.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
          response.setHeader('Content-Length', metadata.size);
          if (request.method === 'HEAD') {
            response.end();
            return;
          }
          const stream = createReadStream(file);
          stream.on('error', (error) => {
            server.config.logger.error(`Journal PDF download failed: ${error.message}`);
            response.destroy(error);
          });
          response.on('close', () => stream.destroy());
          stream.pipe(response);
        } catch (error) {
          const missing = (error as NodeJS.ErrnoException).code === 'ENOENT';
          response.statusCode = missing ? 404 : 500;
          response.end(missing ? 'Journal PDF is not available.' : 'Journal PDF download failed.');
          if (!missing) server.config.logger.error(String(error));
        }
      });
    },
  };
}
