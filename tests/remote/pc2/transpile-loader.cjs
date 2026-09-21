const path = require('node:path');
const ts = require(path.resolve(__dirname, '../../..', 'apps/web/node_modules/typescript'));

// Isolated harness only. The application's real typecheck remains independent.
module.exports = function transpile(source) {
  return ts.transpileModule(source, {
    fileName: this.resourcePath,
    compilerOptions: {
      jsx: ts.JsxEmit.ReactJSX,
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2020,
      esModuleInterop: true,
      sourceMap: true,
    },
  }).outputText;
};
