// T1 independent Next.js app. Generates a vendored snapshot from the shared token SSOT.
// Run locally to refresh; consuming CSS only references semantic/scale variables.
import fs from 'node:fs';
import path from 'node:path';
const source = process.env.ONEFLOW_TOKEN_SOURCE || 'C:/00.프로젝트/75_하네스_클라우드배포/01_프론트엔드/01_토큰/src';
const read = name => JSON.parse(fs.readFileSync(path.join(source, `${name}.json`), 'utf8'));
const primitive = read('primitive'), semantic = read('semantic'), scale = read('scale');
function lookup(obj, key) { return key.split('.').reduce((acc, part) => acc?.[part], obj); }
function value(v) {
  if (typeof v !== 'string') return v;
  return v.replace(/\{([^}]+)\}/g, (_, key) => value(lookup(primitive, key)?.value ?? lookup(scale, key)?.value ?? ''));
}
const vars = [];
function walk(obj, keys = []) {
  if (!obj || typeof obj !== 'object') return;
  if ('value' in obj) { vars.push(`  --${keys.join('-')}: ${value(obj.value)};`); return; }
  if ('light' in obj) { walk(obj.light, keys); return; }
  if ('desktop' in obj) { walk(obj.desktop, keys); return; }
  for (const [key, child] of Object.entries(obj)) if (!key.startsWith('_') && !['comment', 'cr-min'].includes(key)) walk(child, [...keys, key]);
}
walk(semantic); walk(scale);
fs.writeFileSync(new URL('../app/tokens.css', import.meta.url), `/* Generated from shared semantic/scale token SSOT. Do not hand-edit. */\n:root {\n${vars.join('\n')}\n}\n`);
console.log(`Generated ${vars.length} semantic/scale variables.`);
