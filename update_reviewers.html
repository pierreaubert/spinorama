#!/bin/sh
export LOCALE=C
json_pp < docs/assets/metadata.json  | \
    grep -e '"misc-' | \
    grep -v default | \
    sed -e s'/[ \t"":{"]//g' | \
    sed -e 's/misc-//' -e 's/-horizontal//g' -e 's/-vertical//g' | \
    sort -s -f -u | \
    awk '{printf("<option value=\"%s\">%s%s</option>\n", $0, toupper(substr($0,1,1)), substr($0,2));}' > src/website/reviewers.html
