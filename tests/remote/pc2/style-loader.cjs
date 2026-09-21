// Inject the real CSS emitted by Next's CSS loader; do not duplicate CSS rules.
module.exports = function styleLoader() {};
module.exports.pitch = function inject(request) {
  return `import css from ${JSON.stringify('!!' + request)};
const node = document.createElement('style');
node.dataset.n02Source = ${JSON.stringify(this.resourcePath)};
node.textContent = css.toString();
document.head.appendChild(node);
export default css.locals || {};`;
};
