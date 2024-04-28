#!/bin/sh

# warning this section is read by a python script (generate_html) to grab the versions

PLOTLY=2.30.0
HANDLEBARS=4.7.8
BULMA=1.0.0
FONTAWESOME=6.5.2
FUSE=7.0.0
WORKBOX=7.0.0

# end section

ASSETS=./docs
WEBFONTS=./docs/webfonts
SVGS=./docs/svg
DOWNLOADS=./docs/tmp

# main
if ! test -f "${ASSETS}/plotly-${PLOTLY}.min.js"; then
    wget -O${ASSETS}/plotly-${PLOTLY}.min.js https://cdn.plot.ly/plotly-${PLOTLY}.min.js
fi
if ! test -f "${ASSETS}/handlebars-${HANDLEBARS}.min.js"; then
    wget -O${ASSETS}/handlebars-${HANDLEBARS}.min.js https://cdn.jsdelivr.net/npm/handlebars@${HANDLEBARS}/dist/handlebars.min.js
fi
if ! test -f "${ASSETS}/bulma-${BULMA}.min.css"; then
    wget -O${ASSETS}/bulma-${BULMA}.min.css https://cdn.jsdelivr.net/npm/bulma@${BULMA}/css/bulma.min.css
fi
if ! test -f "${ASSETS}/fuse-${FUSE}.min.js"; then
    wget -O${ASSETS}/fuse-${FUSE}.min.js https://cdn.jsdelivr.net/npm/fuse.js@${FUSE}/dist/fuse.min.js
fi

# WORKBOX

npm install workbox-window
cp node_modules/workbox-window/build/workbox-window.prod.mjs docs/workbox-window-${WORKBOX}.min.js
cp node_modules/workbox-window/build/workbox-window.prod.mjs.map docs/workbox-window-${WORKBOX}.min.js.map

# fontawesome
if ! test -f "${ASSETS}/fontawesome-${FONTAWESOME}.min.css"; then
    wget -O${ASSETS}/fontawesome-${FONTAWESOME}.min.css https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/css/all.min.css
fi

# associated fonts
mkdir -p ${WEBFONTS}
if ! test -f "${WEBFONTS}/fa-brands-400.woff2"; then
    wget -O${WEBFONTS}/fa-brands-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-brands-400.woff2
fi
if ! test -f "${WEBFONTS}/fa-solid-900.woff2"; then
    wget -O${WEBFONTS}/fa-solid-900.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-solid-900.woff2
fi
if ! test -f "${WEBFONTS}/fa-regular-400.woff2"; then
    wget -O${WEBFONTS}/fa-regular-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-regular-400.woff2
fi

# associated svg(s) with sprites
mkdir -p ${DOWNLOADS}
if ! test -f "${DOWNLOADS}/fontawesome-free-${FONTAWESOME}-web.zip"; then
    wget -O${DOWNLOADS}/fontawesome-free-${FONTAWESOME}-web.zip https://use.fontawesome.com/releases/v${FONTAWESOME}/fontawesome-free-${FONTAWESOME}-web.zip
    cd ${DOWNLOADS} && unzip fontawesome-free-${FONTAWESOME}-web.zip && cd -
fi

