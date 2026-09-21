import { build } from 'esbuild';
import { createServer } from 'node:http';
import { readFile, stat, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(HERE, '../../..');
export const WEB = path.join(ROOT, 'apps/web');
export const MEDIA = path.join(WEB, 'public/demo');

export async function sourceHashes() {
  const files = ['apps/web/components/WmsScene.tsx', 'apps/web/components/WmsScene.module.css', 'apps/web/app/tokens.css', 'data/fixtures/cases.json', 'data/demo-media-manifest.json', 'server/service.py', 'tests/remote/pc3/harness.tsx', 'tests/remote/pc3/harness.css', 'tests/remote/pc3/harness-server.mjs', 'tests/remote/pc3/clip-mutations.mjs', 'tests/remote/pc3/linked-intake-cases.mjs', 'tests/remote/pc3/run.mjs'];
  return Object.fromEntries(await Promise.all(files.map(async file => [file, await readFile(path.join(ROOT, file)).then(bytes => createHash('sha256').update(bytes).digest('hex')).catch(() => 'missing')])));
}

export function browserExecutable(chromium) {
  const candidates = [process.env.PC3_CHROMIUM, process.env.E2E_CHROMIUM, chromium.executablePath(), 'C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'];
  const found = candidates.find(candidate => candidate && existsSync(candidate));
  if (!found) throw new Error('No installed Chromium executable. Set PC3_CHROMIUM; this test does not download a browser.');
  return found;
}

export async function startHarness(out) {
  await mkdir(out, { recursive: true });
  const compiled = await build({
    entryPoints: [path.join(HERE, 'harness.tsx')], bundle: true, write: false,
    outdir: path.join(out, 'bundle'), sourcemap: 'inline', platform: 'browser',
    format: 'iife', target: 'es2022', jsx: 'automatic',
    tsconfig: path.join(WEB, 'tsconfig.json'), nodePaths: [path.join(WEB, 'node_modules')],
    define: { 'process.env.NODE_ENV': '"development"' },
    alias: { '@': WEB }, logLevel: 'silent',
  });
  const js = compiled.outputFiles.find(file => file.path.endsWith('.js'));
  const css = compiled.outputFiles.find(file => file.path.endsWith('.css'));
  if (!js) throw new Error('Component harness bundle was not created.');
  const state = { mediaFault: null, requests: [] };
  const server = createServer(async (req, res) => {
    const url = new URL(req.url || '/', 'http://127.0.0.1');
    state.requests.push({ time: new Date().toISOString(), method: req.method, path: url.pathname, range: req.headers.range || null, fault: state.mediaFault });
    res.setHeader('Cache-Control', 'no-store');
    try {
      if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405).end(); return; }
      if (url.pathname === '/') {
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        res.end('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PC3 actual WmsScene harness</title><link rel="stylesheet" href="/bundle.css"></head><body><main id="root"></main><script src="/bundle.js"></script></body></html>');
        return;
      }
      if (url.pathname === '/bundle.js') { res.setHeader('Content-Type', 'text/javascript; charset=utf-8'); res.end(js.contents); return; }
      if (url.pathname === '/bundle.css') { res.setHeader('Content-Type', 'text/css; charset=utf-8'); res.end(css?.contents || ''); return; }
      if (url.pathname === '/favicon.ico') { res.writeHead(204).end(); return; }
      if (!url.pathname.startsWith('/demo/')) { res.writeHead(404).end('Harness route missing'); return; }
      const relative = decodeURIComponent(url.pathname.slice('/demo/'.length));
      const file = path.resolve(MEDIA, relative);
      if (!file.startsWith(path.resolve(MEDIA) + path.sep)) { res.writeHead(403).end(); return; }
      const fileStat = await stat(file);
      if (!fileStat.isFile()) { res.writeHead(404).end(); return; }
      if (state.mediaFault === '404') { res.writeHead(404).end('PC3 injected missing media'); return; }
      let data = await readFile(file);
      if (state.mediaFault === 'corrupt') {
        data = Buffer.from(data); data[Math.floor(data.length / 2)] ^= 255;
      }
      res.setHeader('Content-Type', { '.mp4': 'video/mp4', '.wav': 'audio/wav', '.json': 'application/json', '.vtt': 'text/vtt' }[path.extname(file).toLowerCase()] || 'application/octet-stream');
      res.setHeader('Accept-Ranges', 'bytes');
      const range = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range || '');
      if (range) {
        const start = Number(range[1]); const end = Math.min(range[2] ? Number(range[2]) : data.length - 1, data.length - 1);
        if (start > end || start >= data.length) { res.writeHead(416, { 'Content-Range': `bytes */${data.length}` }).end(); return; }
        res.writeHead(206, { 'Content-Range': `bytes ${start}-${end}/${data.length}`, 'Content-Length': end - start + 1 });
        res.end(req.method === 'HEAD' ? undefined : data.subarray(start, end + 1)); return;
      }
      res.setHeader('Content-Length', data.length); res.end(req.method === 'HEAD' ? undefined : data);
    } catch (error) {
      if (!res.headersSent) res.writeHead(error.code === 'ENOENT' ? 404 : 500);
      res.end('Local test asset unavailable');
    }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  return {
    url: `http://127.0.0.1:${server.address().port}`, state,
    close: () => new Promise((resolve, reject) => { server.closeAllConnections(); server.close(error => error ? reject(error) : resolve()); }),
  };
}
