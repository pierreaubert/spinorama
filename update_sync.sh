#!/bin/sh
TARGET=$HOME/src/pierreaubert.github.io/spinorama
# copy
echo "Sync"
rsync -arv --exclude '*.png' --delete ./docs/* $TARGET
rsync -arv --include '*.png' --delete ./docs/pictures/* $TARGET/pictures
# 
rm  -f $TARGET/speakers/*/*/*/*.png
