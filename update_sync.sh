#!/bin/sh
TARGET=$HOME/src/pierreaubert.github.io/spinorama
# copy 
echo "Sync"
rsync -arv --exclude '*.png' --delete ./docs/* $TARGET
rsync -arv --include '*.png' ./docs/pictures/* $TARGET/pictures
rsync -arv --include '*.png' ./docs/logos/* $TARGET/logos
rm  $TARGET/[A-Z]*/*/*/*.png
# evaluate what's new and needs to be changed
cd $TARGET && git status

