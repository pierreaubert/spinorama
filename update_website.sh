TARGET=$HOME/src/spinorama.master/pierreaubert.github.io/spinorama

./minimise_pictures.sh 
./generate_html.py
rsync -arv docs/* $TARGET
rm  $TARGET/[A-Z]*/*/*/*.png
cd $TARGET && git status

