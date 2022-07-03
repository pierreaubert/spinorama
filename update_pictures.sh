#!/bin/sh

# convert is from imagemagick package
sourcedir=datas
targetdir=docs
mkdir -p ${targetdir}/logos
mkdir -p ${targetdir}/pictures
mkdir -p ${targetdir}/help_pictures
for d in "${sourcedir}/pictures"; do
    find $d -type f -name '*.png'| while read pict; do
	smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" "webp"; do
	    smallert=${smaller%.png}.${t}
	    if ! test -f "$smallert"; then
	        convert "$pict" -define jpeg:size=300x500  -thumbnail '400x600>' -gravity center -extent 400x600 "$smallert";
	    fi
        done
    done
    find $d -type f -name '*.jpg'| while read pict; do
        smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" ; do
	    smallert=${smaller%.jpg}.${t}
	    if ! test -f "$smallert"; then
	        convert "$pict" -define jpeg:size=300x500  -thumbnail '400x600>' -gravity center -extent 400x600 "$smallert";
	    fi
        done
        for t in "webp"; do
	    smallerw=${smaller%.jpg}.${t}
	    if ! test -f "$smallerw"; then
	        convert "$pict" -define jpeg:size=300x500  -thumbnail '400x600>' -gravity center -extent 400x600 "$smallerw";
	    fi
        done
    done
done
# copy logs
cp datas/logos/* docs/logos
# copy help pictures
find ./src/website/help_pictures -type f -name '*.png'| while read pict; do
    smaller=$targetdir/help_pictures/`basename $pict`
    for t in "jpg" "webp"; do
	smallert=${smaller%.png}.${t}
	if ! test -f "$smallert"; then
	    convert "$pict" "$smallert";
	fi
    done
done
