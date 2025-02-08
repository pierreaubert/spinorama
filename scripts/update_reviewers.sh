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

export LOCALE=C

AWK=awk
SED=sed

if test "$OS" = "Darwin"  -a "$ARCH" = "arm64" ; then
    AWK=gawk
    SED=gsed
fi

mkdir -p build/website

json_pp < dist/json/metadata.json  | \
    grep -e '"misc-' | \
    grep -v default | \
    $SED -e s'/[ \t"":{"]//g' | \
    $SED -e 's/misc-//' -e 's/-horizontal//g' -e 's/-vertical//g' -e 's/-sealed//g' -e 's/-ported//g' | \
    sort -s -f -u | \
    $AWK -f ./scripts/update_reviewers.awk > build/website/reviewers.html
