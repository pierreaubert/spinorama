#!/bin/sh

# warning this section is read by a python script (generate_html) to grab the versions

PLOTLY=2.32.0
HANDLEBARS=4.7.8
BULMA=1.0.0
FUSE=7.0.0
WORKBOX=7.0.0

# end section

ASSETS=./docs
ASSETS_JS=${ASSETS}/js3rd
ASSETS_CSS=${ASSETS}/css

# BULMA
if ! test -f "${ASSETS}/handlebars-${HANDLEBARS}.min.js"; then
    wget -O${ASSETS_JS}/handlebars-${HANDLEBARS}.min.js https://cdn.jsdelivr.net/npm/handlebars@${HANDLEBARS}/dist/handlebars.min.js
fi
if ! test -f "${ASSETS}/bulma-${BULMA}.min.css"; then
    wget -O${ASSETS_CSS}/bulma-${BULMA}.min.css https://cdn.jsdelivr.net/npm/bulma@${BULMA}/css/bulma.min.css
fi

# PLOTLY
if ! test -f "${ASSETS}/plotly-${PLOTLY}.min.js"; then
    wget -O${ASSETS_JS}/plotly-${PLOTLY}.min.js https://cdn.plot.ly/plotly-${PLOTLY}.min.js
fi

# FUSE.JS
npm install fuse.js
cp node_modules/fuse.js/dist/fuse.min.mjs ${ASSETS_JS}/fuse-${FUSE}.min.mjs

# WORKBOX
npm install workbox-window
cp node_modules/workbox-window/build/workbox-window.prod.mjs ${ASSETS_JS}/workbox-window-${WORKBOX}.min.js
cp node_modules/workbox-window/build/workbox-window.prod.mjs.map ${ASSETS_JS}/workbox-window-${WORKBOX}.min.js.map

