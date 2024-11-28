#!/bin/sh

# warning this section is read by a python script (generate_html) to grab the versions

PLOTLY=2.35.2
HANDLEBARS=4.7.8
BULMA=1.0.2
FUSE=7.0.0
WORKBOX=7.1.0

# end section

ASSETS=./docs
ASSETS_JS=${ASSETS}/js3rd
ASSETS_CSS=${ASSETS}/css
ASSETS_JSON=${ASSETS}/json

mkdir -p ${ASSETS} ${ASSETS_JS} ${ASSETS_CSS} ${ASSETS_JSON}

# handlebars
if ! test -f "${ASSETS_JS}/handlebars-${HANDLEBARS}.min.js"; then
    wget -O${ASSETS_JS}/handlebars-${HANDLEBARS}.min.js https://cdn.jsdelivr.net/npm/handlebars@${HANDLEBARS}/dist/handlebars.min.js
fi

# BULMA
npm install bulma
cp node_modules/bulma/css/bulma.min.css docs/css/bulma-${BULMA}.min.css

# FUSE.JS
npm install fuse.js
cp node_modules/fuse.js/dist/fuse.min.mjs ${ASSETS_JS}/fuse-${FUSE}.min.mjs

# PLOTLY
npm install plotly.js-dist-min
cp node_modules/plotly.js-dist-min/plotly.min.js ${ASSETS_JS}/plotly-${PLOTLY}.min.mjs

# WORKBOX
npm install workbox-window
cp node_modules/workbox-window/build/workbox-window.prod.mjs ${ASSETS_JS}/workbox-window-${WORKBOX}.min.js
cp node_modules/workbox-window/build/workbox-window.prod.mjs.map ${ASSETS_JS}/workbox-window-${WORKBOX}.min.js.map
