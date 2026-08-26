#!/bin/sh

# warning this section is read by a python script (generate_html) to grab the versions

PLOTLY=4.0.0
HANDLEBARS=4.7.9
BULMA=1.0.4
FUSE=7.4.2
# end section

ASSETS=./dist
ASSETS_JS=${ASSETS}/js3rd
ASSETS_CSS=${ASSETS}/css
ASSETS_JSON=${ASSETS}/json

mkdir -p ${ASSETS} ${ASSETS_JS} ${ASSETS_CSS} ${ASSETS_JSON}

# handlebars
if ! test -f "${ASSETS_JS}/handlebars-${HANDLEBARS}.min.js"; then
    wget -O${ASSETS_JS}/handlebars-${HANDLEBARS}.min.js https://cdn.jsdelivr.net/npm/handlebars@${HANDLEBARS}/dist/handlebars.min.js
fi

# BULMA: compile from SCSS to include both light and dark themes
npm install bulma
npx sass --load-path=node_modules src/website/bulma4spin.scss dist/css/bulma-${BULMA}.min.css --style=compressed --no-source-map

# FUSE.JS
npm install fuse.js
cp node_modules/fuse.js/dist/fuse.min.mjs ${ASSETS_JS}/fuse-${FUSE}.min.mjs

# PLOTLY
npm install plotly.js-dist-min
cp node_modules/plotly.js-dist-min/plotly.min.js ${ASSETS_JS}/plotly-${PLOTLY}.min.mjs
