module.exports = {
	globDirectory: 'docs/',
	globPatterns: [
	    '*.{css,js,json}',
	    'icons/*.svg',
	    'svg/*.svg',
	    'webfonts/*.woff2',
	],
	swDest: 'docs/sw.js',
	ignoreURLParametersMatching: [
		/^utm_/,
		/^fbclid$/
	]
};
