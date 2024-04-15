module.exports = {
    // dontCacheBustURLsMatching: ['meta.js', 'meta.min.js'],
    globDirectory: 'docs/',
    globPatterns: [
        '*.{css,json}',
        'icons/*.svg',
        'svg/*.svg',
        'webfonts/*.woff2',
        '{index|download|compare|eqs|misc|onload|plot|scores|similar|statistics|tabs|search}-v*.js',
    ],
    maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
    swDest: 'docs/sw.js',
    ignoreURLParametersMatching: [/^utm_/, /^fbclid$/],
};
