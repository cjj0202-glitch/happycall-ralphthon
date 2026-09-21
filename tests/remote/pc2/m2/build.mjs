import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';

export const HERE=path.dirname(fileURLToPath(import.meta.url));
export const ROOT=path.resolve(HERE,'../../../..');
export const OUT=path.join(ROOT,'.local/pc2-m2-playback');
export async function build() {
  const manifest=JSON.parse(await readFile(path.join(ROOT,'reports/pc2/audio-m2/playback-manifest.json'),'utf8'));
  for (const [name,expected] of Object.entries(manifest.productSources)) {
    const raw=await readFile(path.join(OUT,'product',name));
    if(createHash('sha256').update(raw).digest('hex')!==expected.sha256) throw new Error(`Product snapshot mismatch: ${name}`);
  }
  const require=createRequire(path.join(ROOT,'apps/web/package.json'));
  const bundled=require('next/dist/compiled/webpack/webpack');bundled.init();
  const compiler=bundled.webpack({mode:'development',devtool:false,entry:path.join(HERE,'harness.tsx'),
    output:{path:OUT,filename:'harness.js'},
    resolve:{extensions:['.tsx','.ts','.js','.json'],modules:[path.join(ROOT,'apps/web/node_modules'),'node_modules'],alias:{'@product':path.join(OUT,'product/apps/web')}},
    module:{rules:[
      {test:/\.tsx?$/,exclude:/node_modules/,use:path.join(HERE,'../transpile-loader.cjs')},
      {test:/\.css$/,use:[path.join(HERE,'../style-loader.cjs'),{loader:path.join(HERE,'../css-loader.cjs'),options:{esModule:true,modules:{auto:/\.module\.css$/,localIdentName:'m2_[name]__[local]_[hash:base64:5]'}}}]},
    ]},
    performance:{hints:false}});
  await new Promise((resolve,reject)=>compiler.run((error,stats)=>compiler.close(()=>error?reject(error):stats.hasErrors()?reject(new Error(stats.toString({all:false,errors:true}))):resolve())));
  await mkdir(OUT,{recursive:true});
  await writeFile(path.join(OUT,'index.html'),'<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>N02-M2 후보 검증</title></head><body><div id="root"></div><script src="/harness.js"></script></body></html>');
  return manifest;
}
