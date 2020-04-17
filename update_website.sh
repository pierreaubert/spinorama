TARGET=$HOME/src/pierreaubert.github.io/spinorama

./minimise_pictures.sh
if not ./generate_meta.py --log-level=DEBUG; then
    print "Generate meta(data) failed!"
    exit 
fi
./generate_graphs.py --only-compare=True --log-level=DEBUG
./generate_stats.py --log-level=DEBUG
./generate_html.py --log-level=DEBUG
rsync -arv --delete docs/* $TARGET
# rm  $TARGET/(assets|compare|stats)/*\ 2.*
rm  $TARGET/[A-Z]*/*/*/*.png
cd $TARGET && git status

