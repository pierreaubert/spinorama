#!/bin/sh
export LOCALE=C
json_pp < docs/assets/metadata.json  | \
    grep -e '"misc-' | \
    grep -v default | \
    sed -e s'/[ \t"":{"]//g' | \
    sed -e 's/misc-//' -e 's/-horizontal//g' -e 's/-vertical//g' -e 's/-sealed//g' -e 's/-ported//g' | \
    sort -s -f -u | \
    awk '{val=toupper(substr($0,1,1)); name=substr($0,2); if (length($0) < 4 ) { val=""; name=toupper($0); } printf("<option value=\"%s\">%s%s</option>\n", $0, val, name);}' > src/website/reviewers.html
