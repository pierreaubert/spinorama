TARGET=$HOME/src/pierreaubert.github.io/spinorama

# update logos and speakers picture
./minimise_pictures.sh
# recompute metadata for all speakers
rm -f docs/assets/metadata.json
./generate_meta.py
rm -f docs/compare/*.json
./generate_compare.py
# generate all graphs if some are missing
rm -fr /tmp/ray
./ray_graphs.py
# generate all jpg if some are missing
./minimise_pictures.sh
# generate stats
rm -f docs/stats/*.json
./generate_stats.py
# generate website
./generate_html.py
# copy 
rsync -arv --delete docs/* $TARGET
# remove unneeded files
# rm  $TARGET/(assets|compare|stats)/*\ 2.*
rm  $TARGET/[A-Z]*/*/*/*.png
# evaluate what's new and needs to be changed
cd $TARGET && git status

