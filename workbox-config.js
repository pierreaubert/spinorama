module.exports = {
	globDirectory: 'docs/',
	globPatterns: [
		'**/*.{css,js,json,png,ico,svg,txt,ttf,woff2}'
	],
	swDest: 'docs/sw.js',
	ignoreURLParametersMatching: [
		/^utm_/,
		/^fbclid$/
	]
};