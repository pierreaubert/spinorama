#!/bin/sh
# A library to display spinorama charts
#
# Copyright (C) 2020-2024 Pierre Aubert pierre(at)spinorama(dot)org
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


# convert is from imagemagick package
sourcedir=datas
targetdir=docs
mkdir -p ${targetdir}/icons
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
mkdir -p docs/icons
cp datas/icons/* docs/icons
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
