import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(HERE, '../../..');
export const OUT = path.join(ROOT, '.local/pc2-harness');
const appRequire = createRequire(path.join(ROOT, 'apps/web/package.json'));

export async function buildHarness() {
  await mkdir(OUT, { recursive: true });
  const bundled = appRequire('next/dist/compiled/webpack/webpack');
  bundled.init();
  const compiler = bundled.webpack({
    mode: 'development', devtool: 'source-map',
    entry: path.join(HERE, 'harness.tsx'),
    output: { path: OUT, filename: 'harness.js' },
    resolve: {
      extensions: ['.tsx', '.ts', '.js', '.json'],
      modules: [path.join(ROOT, 'apps/web/node_modules'), 'node_modules'],
      alias: { '@': path.join(ROOT, 'apps/web') },
    },
    module: { rules: [
      { test: /\.tsx?$/, exclude: /node_modules/, use: path.join(HERE, 'transpile-loader.cjs') },
      { test: /\.css$/, use: [
        path.join(HERE, 'style-loader.cjs'),
        { loader: path.join(HERE, 'css-loader.cjs'), options: { esModule: true, modules: { auto: /\.module\.css$/, localIdentName: 'n02_[name]__[local]_[hash:base64:5]' } } },
      ] },
    ] },
    performance: { hints: false },
  });
  await new Promise((resolve, reject) => compiler.run((error, stats) => {
    compiler.close(() => {});
    if (error) return reject(error);
    if (stats.hasErrors()) return reject(new Error(stats.toString({ all: false, errors: true })));
    resolve();
  }));
  await writeFile(path.join(OUT, 'index.html'), '<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>N02 isolated CallReview</title></head><body><div id="root"></div><script src="/harness.js"></script></body></html>');
  return OUT;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await buildHarness();
  console.log(`Built actual CallReview at ${OUT}`);
}
