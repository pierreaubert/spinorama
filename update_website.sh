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
if ! test $?; then
    echo "Failed after generate graph!"
    exit 1;
fi
# recompute metadata for all speakers
rm -f docs/assets/metadata.json
./generate_meta.py
if ! test $?; then
    echo "Failed after generate meta!"
    exit 1;
fi
rm -f docs/compare/*.json
./generate_compare.py
if ! test $?; then
    echo "Failed after generate compare!"
    exit 1;
fi
# generate all jpg if some are missing
./update_pictures.sh
# generate stats
rm -f docs/stats/*.json
./generate_stats.py
if ! test $?; then
    echo "Failed after generate statistics!"
    exit 1;
fi
# generate website
sh ./update_brands.sh
./generate_html.py
if ! test $?; then
    echo "Failed after generate HTML!"
    exit 1;
fi
./check_html.py
if ! test $?; then
    echo "Failed after checking HTML!"
    exit 1;
fi
# copy 
TARGET=$HOME/src/pierreaubert.github.io/spinorama
./update_sync.sh
if ! test $?; then
    echo "Update $TARGET failed!"
    exit 1;
fi
# evaluate what's new and needs to be changed
cd ${TARGET} && git status
exit 0;

