#!/bin/sh
TARGET=$HOME/src/pierreaubert.github.io/spinorama
# check
command=$(grep internet-box docs/*.html | wc -l)
if [ $command -ne 0 ]; then
    echo "KO found dev url in prod site"
    exit 1;
else
    echo "OK checking for dev site in prod"
fi
# copy
echo "Sync"
rsync -arv --exclude '*.png' --delete ./docs/* $TARGET
rsync -arv --include '*.png' --delete ./docs/pictures/* $TARGET/pictures
rsync -arv --include '*.png' --delete ./docs/help_pictures/* $TARGET/help_pictures
# 
rm  -f $TARGET/speakers/*/*/*/*.png
