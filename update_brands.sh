#!/bin/sh
export LOCALE=C
json_pp < docs/assets/metadata.json  | \
    grep '"brand" : ' | \
    cut -d: -f 2 | \
    cut -b 2- | \
    sed -e 's/[,"]//g' | \
    sort -s -V -f -u | \
    awk '{printf("<option value=\"%s\">%s</option>\n", $0, $0);}' > src/website/brands.html
