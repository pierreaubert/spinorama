TARGET=$HOME/src/pierreaubert.github.io/spinorama

rm -f docs/assets/metadata.json
./generate_meta.py
rm -f docs/compare/*.json
./generate_graphs.py
./minimise_pictures.sh
rm -f docs/stats/*.json
./generate_stats.py
./generate_html.py
rsync -arv --delete docs/* $TARGET
# rm  $TARGET/(assets|compare|stats)/*\ 2.*
rm  $TARGET/[A-Z]*/*/*/*.png
cd $TARGET && git status

