#!/bin/sh

# convert is from imagemagick package
targetdir=./docs/metadata
for d in 'pictures' 'logos'; do
    for pict in `ls datas/$d/*.jpg`; do
	smaller=$targetdir${pict#datas\/$d}
	if ! test -f "$smaller"; then
            echo convert "$smaller";
            echo convert "datas/$d$pict" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$$smaller";
	fi
    done
done

# reduce size of large image
find docs  -type f -name '*_large.png' -print | while read pict; do
    if ! test -f "${pict#_large.png}.png"; then
	convert "$pict" -quality 25 "${pict#_large.png}.png"
    fi
done
