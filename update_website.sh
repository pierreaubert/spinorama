#!/bin/sh
TARGET=$HOME/src/pierreaubert.github.io/spinorama
echo "Update starts"
export PYTHONPATH=src:.

# update logos and speakers picture
./minimise_pictures.sh
# generate all graphs if some are missing
rm -fr /tmp/ray
./generate_graphs.py
# recompute metadata for all speakers
rm -f docs/assets/metadata.json
./generate_meta.py
rm -f docs/compare/*.json
./generate_compare.py
# generate all jpg if some are missing
./minimise_pictures.sh
# generate stats
rm -f docs/stats/*.json
./generate_stats.py
# generate website
sh ./update_brands.sh
./generate_html.py
# copy 
echo "Sync"
rsync -arv --exclude '*.png' --delete ./docs/* $TARGET
rsync -arv --include '*.png' ./docs/pictures/* $TARGET/pictures
rsync -arv --include '*.png' ./docs/logos/* $TARGET/logos
# remove unneeded files
# rm  $TARGET/(assets|compare|stats)/*\ 2.*
rm  $TARGET/[A-Z]*/*/*/*.png
# evaluate what's new and needs to be changed
cd $TARGET && git status

