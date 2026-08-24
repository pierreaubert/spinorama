#!/bin/sh
# A library to display spinorama charts
#
# Copyright (C) 2020-2025 Pierre Aubert pierre(at)spinorama(dot)org
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

OS=$(uname)
ARCH=$(uname -a | awk '{print $NF}')

CONVERT=convert
if test "$OS" = "Darwin"  -a "$ARCH" = "arm64" ; then
    CONVERT="/opt/homebrew/bin/magick"
fi

# convert is from imagemagick package
sourcedir=datas
targetdir=dist
mkdir -p ${targetdir}/pictures
for d in "${sourcedir}/pictures"; do
    find $d -type f -name '*.png'| while read pict; do
	smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" "webp"; do
	    smallert=${smaller%.png}.${t}
	    if ! test -f "$smallert" || test "$pict" -nt "$smallert"; then
	        "$CONVERT" "$pict" -define jpeg:size=300x500  -thumbnail '400x600>' -gravity center -extent 400x600 "$smallert";
	    fi
        done
    done
    find $d -type f -name '*.jpg'| while read pict; do
        smaller=$targetdir${pict#$sourcedir}
        for t in "jpg" ; do
	    smallert=${smaller%.jpg}.${t}
	    if ! test -f "$smallert" || test "$pict" -nt "$smallert"; then
	        "$CONVERT" "$pict" -define jpeg:size=300x500  -thumbnail '400x600>' -gravity center -extent 400x600 "$smallert";
	    fi
        done
        for t in "webp"; do
	    smallerw=${smaller%.jpg}.${t}
	    if ! test -f "$smallerw" || test "$pict" -nt "$smallerw"; then
	        "$CONVERT" "$pict" -define jpeg:size=300x500  -thumbnail '400x600>' -gravity center -extent 400x600 "$smallerw";
	    fi
        done
    done
done
# copy logs
for icon in datas/icons/*; do
    target="dist/pictures/$(basename "$icon")"
    if test ! -f "$target" || ! cmp -s "$icon" "$target"; then
        cp -p "$icon" "$target"
    fi
done
