#!/bin/bash
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

echo "Update starts"
mkdir -p .cache
mkdir -p build/website
export THEPYTHON=python3.12
export PYTHONPATH=src:src/website:src/spinorama:.

# check meta
command=$(${THEPYTHON} ./scripts/check_meta.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO checking metadata ($status)";
    exit 1;
else
    echo "OK checking metadata"
fi

# update logos and speakers picture
./scripts/update_pictures.sh

# generate all graphs if some are missing
command=$(${THEPYTHON} ./generate_graphs.py --update-cache)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate graph!"
    exit 1;
else
    echo "OK after generate graph!"
fi

# potential bug in generate_meta
rm -f dist/json/*

# recompute metadata for all speakers
command=$(${THEPYTHON} ./generate_meta.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate meta!"
    exit 1;
else
    echo "OK after generate meta!"
fi

# generate all jpg if some are missing
./scripts/update_pictures.sh

# generate eq filters
command=$(${THEPYTHON} ./generate_peqs.py --generate-images-only)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate eq filters!"
    exit 1;
else
    echo "OK after generate eq filters!"
fi

# generate radar
command=$(${THEPYTHON} ./generate_radar.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate radar!"
    exit 1;
else
    echo "OK after generate radar!"
fi

# generate eq_compare
command=$(${THEPYTHON} ./generate_eq_compare.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate EQ compare!"
    exit 1;
else
    echo "OK after generate EQ compare!"
fi

# generate status
command=$(${THEPYTHON} ./generate_stats.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate statistics!"
    exit 1;
else
    echo "OK after generate statistics!"
fi

# generate status
today="$(date "+%Y-%m-%d")"
command=$(${THEPYTHON} ./generate_stats.py --print=eq_csv --log-level=ERROR > build/spinorama.org-${today}.csv 2>&1)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate statistics in csv!"
    exit 1;
else
    echo "OK after generate statistics in csv!"
fi

# generate list of svgs
command=$(${THEPYTHON} ./scripts/svg2symbols.py > build/website/symbols.html)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after update symbols!"
    rm -f build/website/symbols.html
    exit 1;
else
    echo "OK after update symbols"
fi

# generate list of brands
command=$(./scripts/update_brands.sh)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after update brands!"
    rm -f build/website/brands.html
    exit 1;
else
    echo "OK after update brands"
fi

# generate list of reviewers
command=$(./scripts/update_reviewers.sh)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after update reviewers!"
    rm -f build/website/reviewers.html
    exit 1;
else
    echo "OK after update reviewers"
fi

command=$(${THEPYTHON} ./generate_html.py --dev --optim --sitedev=https://dev.spinorama.org)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate HTML!"
    exit 1;
else
    echo "OK after generate HTML!"
fi

#command=$(type -P quarto)
#status=$?
#if [ $status -ne 0 ]; then
#    command=$(quarto render manual/*.qmd --to html)
#    qstatus=$?
#    if [ $qstatus -ne 0 ]; then
#	echo "KO after generate HTML manual!"
#	# does not work lauched from the script but does work in the shell
#    else
#	echo "OK after generate HTML manual!"
#    fi
#else
#    echo "Quarto is not available, skipping HTML manual!"
#fi

command=$(./scripts/check_html.sh)
if [ $status -ne 0 ]; then
    echo "KO after checking HTML!"
    exit 1;
else
    echo "OK after checking HTML!"
fi

# copy
command=$(./scripts/update_dev.sh)
status=$?
if [ $status -ne 0 ]; then
    echo "KO Update $TARGET!"
    exit 1;
else
    echo "OK Update $TARGET!"
fi
exit 0;
