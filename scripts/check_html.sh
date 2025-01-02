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
status=0

for d in docs/*.html; do
    sz=0
    if test "$OS" = "Linux"; then
	sz=$(stat -c %s "$d")
    elif test "$OS" = "Darwin"; then
	sz=$(stat -f "%z" "$d")
    fi
    if test $sz -eq 0; then
        status=1;
        echo "$d is empty (ERROR)";
    elif test "$d" != "docs/icons.html"; then
        msg=$(./node_modules/.bin/w3c-html-validator --quiet "$d");
        if test -n "$msg"; then
            status=1;
            echo "Linting $d (ERROR)";
    	    ./node_modules/.bin/w3c-html-validator "$d";
        fi
    fi
done

if test $status -eq 0; then
    echo "all files are clean!";
    exit 0;
else
    exit 1;
fi
