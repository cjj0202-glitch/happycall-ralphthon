// Exercise the deployed request URL without a browser, server or paid API.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('../../apps/web/node_modules/typescript');
const source = fs.readFileSync(path.resolve(__dirname, '../../apps/web/lib/api.ts'), 'utf8');
const compiled = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
}}).outputText;

for (const [label, env, expected] of [
  ['production defaults to the page origin', {NODE_ENV:'production'}, '/api/cases'],
  ['development retains the local API', {NODE_ENV:'development'}, 'http://127.0.0.1:8100/api/cases'],
  ['explicit same origin is preserved', {NODE_ENV:'development', NEXT_PUBLIC_API_BASE:''}, '/api/cases'],
  ['explicit HTTPS API has no double slash', {NODE_ENV:'production', NEXT_PUBLIC_API_BASE:'https://api.example.test/'}, 'https://api.example.test/api/cases'],
]) {
  test(label, async () => {
    const calls = [];
    const sandbox = {exports:{}, process:{env}, AbortController, setTimeout, clearTimeout,
      fetch: async (url, options) => { calls.push({url, options}); return {ok:true, json:async()=>({cases:[]})}; }};
    vm.runInNewContext(compiled, sandbox);
    const result = await sandbox.exports.request('/api/cases');
    assert.equal(result.cases.length, 0);
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, expected);
    assert.equal(calls[0].options.cache, 'no-store');
    assert.equal(calls[0].options.headers['X-Demo-Role'], 'counselor');
  });
}
