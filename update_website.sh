TARGET=$HOME/src/pierreaubert.github.io/spinorama

./minimise_pictures.sh
./generate_meta.py
./generate_graphs.py
./generate_stats.py
./generate_html.py
rsync -arv --delete docs/* $TARGET
# rm  $TARGET/(assets|compare|stats)/*\ 2.*
rm  $TARGET/[A-Z]*/*/*/*.png
cd $TARGET && git status

