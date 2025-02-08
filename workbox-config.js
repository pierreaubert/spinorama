module.exports = {
    globDirectory: 'dist/',
    globPatterns: ['*.{html,xml,txt,svg}', 'css/*.css', 'js/*-v5.min.js', 'js3rd/*.{js,mjs}', 'json/{eqdata,metadata-*}.json'],
    maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
    swDest: 'dist/sw.js',
    ignoreURLParametersMatching: [/^utm_/, /^fbclid$/],
};
