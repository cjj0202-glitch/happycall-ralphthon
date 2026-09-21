const { createRequire } = require('node:module');
const path = require('node:path');
const appRequire = createRequire(path.resolve(__dirname, '../../..', 'apps/web/package.json'));
const loader = appRequire('next/dist/build/webpack/loaders/css-loader/src').default;

// Next's real CSS compiler expects its trace/postcss context. Supply that build
// context without starting or changing the shared Next application.
module.exports = function nextCss(content, map, meta) {
  const originalOptions = this.getOptions();
  const context = Object.create(this);
  context.currentTraceSpan = { traceChild: () => ({ traceAsyncFn: action => action() }) };
  context.getOptions = () => ({
    ...originalOptions,
    modules: { ...originalOptions.modules, getLocalIdent: appRequire('next/dist/build/webpack/config/blocks/css/loaders/getCssModuleLocalIdent').getCssModuleLocalIdent },
    postcss: async () => ({ postcss: appRequire('postcss') }),
  });
  return loader.call(context, content, map, meta);
};
