TARGET=$HOME/src/pierreaubert.github.io/spinorama

./minimise_pictures.sh
./generate_meta.py
./generate_graphs.py --only-compare=True
./generate_stats.py
./generate_html.py
rsync -arv --delete docs/* $TARGET
<<<<<<< HEAD
rm  $TARGET/(assets|compare|stats)/*\ 2.*
=======
>>>>>>> 45f20c4475d9c39f848a277e755a3b0c677628b5
rm  $TARGET/[A-Z]*/*/*/*.png
cd $TARGET && git status

