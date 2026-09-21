import http from 'node:http';
import path from 'node:path';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {ROOT,OUT} from './build.mjs';

export async function serve(manifest) {
  const routes=new Map([
    ['/',{raw:await readFile(path.join(OUT,'index.html')),type:'text/html; charset=utf-8'}],
    ['/harness.js',{raw:await readFile(path.join(OUT,'harness.js')),type:'text/javascript; charset=utf-8'}],
  ]);
  for (const asset of Object.values(manifest.assets)) {
    const raw=await readFile(path.join(ROOT,asset.localPath));
    if (raw.length!==asset.bytes||createHash('sha256').update(raw).digest('hex')!==asset.sha256) throw new Error('Audio bytes/hash mismatch');
    routes.set(asset.url,{raw,type:'audio/wav'});
  }
  const requests=[];
  const server=http.createServer((req,res)=>{
    const pathname=new URL(req.url,'http://127.0.0.1').pathname;
    const item=routes.get(pathname);
    if(pathname==='/favicon.ico'){res.writeHead(204).end();return;}
    if(!['GET','HEAD'].includes(req.method)||!item){res.writeHead(404).end();return;}
    const {raw,type}=item;
    const range=req.headers.range&&/^bytes=(\d+)-(\d*)$/.exec(req.headers.range);
    const start=range?Number(range[1]):0,end=range&&range[2]?Math.min(Number(range[2]),raw.length-1):raw.length-1;
    if(start> end||start>=raw.length){res.writeHead(416).end();return;}
    const status=range?206:200;
    requests.push({at:new Date().toISOString(),path:pathname,method:req.method,status,start,end});
    res.writeHead(status,{'Content-Type':type,'Content-Length':end-start+1,'Accept-Ranges':'bytes','Cache-Control':'no-store',...(range?{'Content-Range':`bytes ${start}-${end}/${raw.length}`}:{})});
    res.end(req.method==='HEAD'?undefined:raw.subarray(start,end+1));
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const address=server.address();
  return {origin:`http://127.0.0.1:${address.port}`,address,requests,
    close:()=>new Promise(resolve=>{server.close(resolve);server.closeIdleConnections();server.closeAllConnections();})};
}
