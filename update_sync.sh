#!/bin/sh
TARGET=$HOME/src/pierreaubert.github.io/spinorama
# copy
echo "Sync"
rsync -arv --exclude '*.png' --delete ./docs/* $TARGET
rsync -arv --include '*.png' --delete ./docs/pictures/* $TARGET/pictures
rsync -arv --include '*.png' --delete ./docs/logos/* $TARGET/logos
#
rm  -f $TARGET/[A-Z]*/*/*/*.png
