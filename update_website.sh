TARGET=$HOME/src/pierreaubert.github.io/spinorama

./minimise_pictures.sh
./generate_graphs.py --only-compare=True
./generate_meta.py
./generate_stats.py
./generate_html.py
rsync -arv --delete docs/* $TARGET
rm  $TARGET/[A-Z]*/*/*/*.png
cd $TARGET && git status

