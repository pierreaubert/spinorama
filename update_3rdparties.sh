#!/bin/sh

PLOTLY=2.27.0
HANDLEBARS=4.7.7
BULMA=0.9.4
FONTAWESOME=6.5.1
FUSE=6.6.2

ASSETS=./docs/assets
WEBFONTS=./docs/webfonts
SVGS=./docs/svg
DOWNLOADS=./docs/tmp

# main
#wget -O${ASSETS}/plotly-${PLOTLY}.min.js https://cdn.plot.ly/plotly-${PLOTLY}.min.js
#wget -O${ASSETS}/handlebars-${HANDLEBARS}.min.js https://cdn.jsdelivr.net/npm/handlebars@${HANDLEBARS}/dist/handlebars.min.js
#wget -O${ASSETS}/bulma-${BULMA}.min.css https://cdn.jsdelivr.net/npm/bulma@${BULMA}/css/bulma.min.css
#wget -O${ASSETS}/fuse-${FUSE}.min.js https://cdn.jsdelivr.net/npm/fuse.js@${FUSE}/dist/fuse.min.js

# fontawesome
#wget -O${ASSETS}/fontawesome-${FONTAWESOME}.min.css https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/css/all.min.css

# associated fonts
#mkdir -p ${WEBFONTS}
#wget -O${WEBFONTS}/fa-brands-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-brands-400.woff2
#wget -O${WEBFONTS}/fa-solid-900.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-solid-900.woff2
#wget -O${WEBFONTS}/fa-regular-400.woff2 https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@${FONTAWESOME}/webfonts/fa-regular-400.woff2

# associated svg(s) with sprites
#mkdir -p ${DOWNLOADS}
#wget -O${DOWNLOADS}/fontawesome-free-${FONTAWESOME}-web.zip https://use.fontawesome.com/releases/v${FONTAWESOME}/fontawesome-free-${FONTAWESOME}-web.zip
#cd ${DOWNLOADS} && unzip fontawesome-free-${FONTAWESOME}-web.zip

#mkdir -p ${SVGS}

echo "SOLID"
FASOLID=$(grep 'fas' ./src/website/*.html | grep -e 'fa[-]' | sed -e 's/.*class="//' -e 's/".*//'  -e 's/fas //g' -e 's/fa-solid //'| sort -u)
for fa in $FASOLID; do
    cp "${DOWNLOADS}/fontawesome-free-${FONTAWESOME}-web/svgs/solid/${fa#fa-}.svg" ${SVGS}
done

echo "BRAND"
FABRAND=$(grep 'fab' ./src/website/*.html | grep -e 'fa[-]' | sed -e 's/.*class="//' -e 's/".*//'  -e 's/fab //g' -e 's/fa-brand //'| sort -u)
for fa in $FABRAND; do
    cp "${DOWNLOADS}/fontawesome-free-${FONTAWESOME}-web/svgs/brands/${fa}" ${SVGS}
done

echo "REGULAR"
FAREGULAR=$(grep 'regular' ./src/website/*.html | sed -e 's/.*class="//' -e 's/".*//'  -e 's/fas //g' -e 's/fa-regular //'| sort -u)
for fa in $FAREGULAR; do
    cp "${DOWNLOADS}/fontawesome-free-${FONTAWESOME}-web/svgs/regular/${fa}" ${SVGS}
done
