#!/bin/sh
echo "Update starts"
export PYTHONPATH=src:.

# check meta
./check_meta.py
if ! test $?; then
    echo "Failed after checking metadata!"
    exit 1;
fi
# update logos and speakers picture
./update_pictures.sh
# generate all graphs if some are missing
rm -fr /tmp/ray
./generate_graphs.py
# recompute metadata for all speakers
rm -f docs/assets/metadata.json
./generate_meta.py
rm -f docs/compare/*.json
./generate_compare.py
# generate all jpg if some are missing
./update_pictures.sh
# generate stats
rm -f docs/stats/*.json
./generate_stats.py
# generate website
sh ./update_brands.sh
./generate_html.py
./check_html.py
if ! test $?; then
    echo "Failed after checking HTML!"
    exit 1;
fi
# copy 
./update_sync.sh
# evaluate what's new and needs to be changed
TARGET=$HOME/src/pierreaubert.github.io/spinorama
cd ${TARGET} && git status
exit 0;

