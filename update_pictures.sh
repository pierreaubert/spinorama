#!/bin/sh

# convert is from imagemagick package
sourcedir=datas
targetdir=docs
mkdir -p ${targetdir}/logos
mkdir -p ${targetdir}/pictures
for d in "${sourcedir}/pictures"; do
    find $d -type f -name '*.png'| while read pict; do
	smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" "webp"; do
	    smallert=${smaller%.png}.${t}
	    if ! test -f "$smallert"; then
	        convert "$pict" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$smallert";
	    fi
        done
    done
    find $d -type f -name '*.jpg'| while read pict; do
        smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" "webp"; do
	    smallert=${smaller%.jpg}.${t}
	    if ! test -f "$smaller"; then
	        convert "$pict" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$smallert";
	    fi
        done
    done
done
# copy logs
cp datas/logos/* docs/logos
