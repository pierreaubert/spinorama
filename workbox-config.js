module.exports = {
    globDirectory: 'docs/',
    globPatterns: ['*.{js,html,xml,txt,svg}', '*/*.{css,js,mjs,json}'],
    maximumFileSizeToCacheInBytes: 4 * 1024 * 1024,
    swDest: 'docs/sw.js',
    ignoreURLParametersMatching: [/^utm_/, /^fbclid$/],
};