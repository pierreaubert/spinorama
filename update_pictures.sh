#!/bin/sh

# convert is from imagemagick package
sourcedir=datas
targetdir=docs
mkdir -p ${targetdir}/logos
mkdir -p ${targetdir}/pictures
for d in "${sourcedir}/pictures"; do
    find $d -type f -name '*.png'| while read pict; do
	smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" "webp" "avif"; do
	    smallert=${smaller%.png}.${t}
	    if ! test -f "$smallert"; then
	        echo convert "$pict" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$smallert";
	    fi
        done
    done
    find $d -type f -name '*.jpg'| while read pict; do
        smaller=$targetdir${pict#$sourcedir}
        for t in "webp" "avif"; do
	    smallert=${smaller%.jpg}.${t}
	    if ! test -f "$smaller"; then
	        convert "$pict" -define jpeg:size=300x500  -thumbnail '200x300>' -gravity center -extent 200x300 "$smallert";
	    fi
        done
    done
done
# copy logs
cp datas/logos/* docs/logos

# reduce size of large image
find docs  -type f -name '*_large.png' -print | while read pict; do
    for t in "jpg" "webp" "avif"; do
        target="${pict%_large.png}.${t}"
        if ! test -f "${target}"; then
            if [ "$t" = "jpg" ]; then
	        convert "$pict" -quality 75 "${target}"
            else
	        convert "$pict" "${target}"
            fi
        fi
    done
done
