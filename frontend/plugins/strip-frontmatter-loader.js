module.exports = function (source) {
  return source.replace(/^---[\s\S]*?---\n/, '');
};
