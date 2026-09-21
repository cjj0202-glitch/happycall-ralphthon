import http from 'node:http';
import path from 'node:path';
import { readFile, stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { ROOT, OUT } from './build.mjs';

function wave(seconds, silent = false) {
  const samples = Math.floor(seconds * 16000), bytes = samples * 2;
  const b = Buffer.alloc(44 + bytes);
  b.write('RIFF'); b.writeUInt32LE(36 + bytes, 4); b.write('WAVEfmt ', 8);
  b.writeUInt32LE(16, 16); b.writeUInt16LE(1, 20); b.writeUInt16LE(1, 22);
  b.writeUInt32LE(16000, 24); b.writeUInt32LE(32000, 28); b.writeUInt16LE(2, 32); b.writeUInt16LE(16, 34);
  b.write('data', 36); b.writeUInt32LE(bytes, 40);
  for (let i = 0; i < samples; i++) b.writeInt16LE(silent ? 0 : Math.round(Math.sin(2 * Math.PI * 440 * i / 16000) * 2000), 44 + i * 2);
  return b;
}

export async function startServer(port = 3122) {
  const requests = [];
  const generated = { '/test-audio/short.wav': wave(3), '/test-audio/silent.wav': wave(0.4, true), '/test-audio/zero.wav': wave(0, true), '/test-audio/damaged.wav': Buffer.from('N02 deliberately invalid WAV') };
  const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    requests.push({ at: new Date().toISOString(), method: req.method, pathname: url.pathname });
    if (!['GET', 'HEAD'].includes(req.method)) { res.writeHead(405).end(); return; }
    let buffer, file;
    if (url.pathname in generated) buffer = generated[url.pathname];
    else if (/^\/demo\/CASE-000[12]\.wav$/.test(url.pathname)) file = path.join(ROOT, 'apps/web/public', url.pathname);
    else if (url.pathname === '/') file = path.join(OUT, 'index.html');
    else if (/^\/harness\.js(?:\.map)?$/.test(url.pathname)) file = path.join(OUT, url.pathname);
    else { res.writeHead(404).end('Not found'); return; }
    try {
      const size = buffer ? buffer.length : (await stat(file)).size;
      const isAudio = url.pathname.endsWith('.wav');
      const type = isAudio ? 'audio/wav' : url.pathname.endsWith('.js') ? 'text/javascript; charset=utf-8' : url.pathname.endsWith('.map') ? 'application/json' : 'text/html; charset=utf-8';
      const range = req.headers.range && /^bytes=(\d+)-(\d*)$/.exec(req.headers.range);
      const start = range ? Number(range[1]) : 0, end = range && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
      if (start >= size || start > end) { res.writeHead(416).end(); return; }
      res.writeHead(range ? 206 : 200, { 'Content-Type': type, 'Content-Length': end - start + 1, 'Accept-Ranges': 'bytes', 'Cache-Control': 'no-store', ...(range ? { 'Content-Range': `bytes ${start}-${end}/${size}` } : {}) });
      if (req.method === 'HEAD') res.end();
      else if (buffer) res.end(buffer.subarray(start, end + 1));
      else {
        const stream = createReadStream(file, { start, end });
        stream.on('error', error => { requests.push({ pathname: url.pathname, readError: error.code || error.message }); res.destroy(error); });
        stream.pipe(res);
      }
    } catch (error) { res.writeHead(404).end('Local file unavailable'); }
  });
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(port, '127.0.0.1', resolve); });
  return { server, requests, origin: `http://127.0.0.1:${port}`, stop: () => new Promise(resolve => {
    server.close(resolve);
    // Only sockets owned by this isolated server are closed, after browser use.
    server.closeIdleConnections();
    server.closeAllConnections();
  }) };
}
