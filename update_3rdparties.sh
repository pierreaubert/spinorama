#!/bin/sh

PLOTLY=2.27.0
HANDLEBARS=4.7.7
BULMA=0.9.4
FONTAWESOME=6.4.2
FUSE=6.6.2

ASSETS=./docs/assets
WEBFONTS=./docs/webfonts

wget -O${ASSETS}/plotly-${PLOTLY}.min.js https://cdn.plot.ly/plotly-${PLOTLY}.min.js
wget -O${ASSETS}/handlebars-${HANDLEBARS}.min.js https://cdn.jsdelivr.net/npm/handlebars@${HANDLEBARS}/dist/handlebars.min.js
wget -O${ASSETS}/bulma-${BULMA}.min.css https://cdn.jsdelivr.net/npm/bulma@${BULMA}/css/bulma.min.css
wget -O${ASSETS}/fuse-${FUSE}.min.js https://cdn.jsdelivr.net/npm/fuse.js@${FUSE}/dist/fuse.min.js

wget -O${ASSETS}/fontawesome-${FONTAWESOME}.min.css https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/css/all.min.css
mkdir -p ${WEBFONTS}
wget -O${WEBFONTS}/fa-brands-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-brands-400.woff2
wget -O${WEBFONTS}/fa-solid-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-solid-400.woff2
wget -O${WEBFONTS}/fa-solid-900.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-solid-900.woff2
wget -O${WEBFONTS}/fa-regular-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-regular-400.woff2

