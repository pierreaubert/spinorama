module.exports = {
    // dontCacheBustURLsMatching: ['js/meta-v2.min.js'],
    globDirectory: 'docs/',
    globPatterns: [
        'css/*.css',
        'js3rd/*.js',
        'js/*-v*.js',
        'json/*.json',
        '*.html',
    ],
    maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
    swDest: 'docs/js/sw.js',
    ignoreURLParametersMatching: [/^utm_/, /^fbclid$/],
};
