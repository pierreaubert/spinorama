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

mkdir -p .cache
mkdir -p build/website
SECONDS=0
LOCK_DIR=.cache/update_website.lock

release_lock() {
    rm -f "$LOCK_DIR/pid"
    rmdir "$LOCK_DIR" 2>/dev/null || true
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    lock_pid=""
    if [ -f "$LOCK_DIR/pid" ]; then
        lock_pid=$(cat "$LOCK_DIR/pid")
    fi
    case "$lock_pid" in
        ''|*[!0-9]*) ;;
        *)
            if kill -0 "$lock_pid" 2>/dev/null; then
                echo "Another update_website.sh run is active (PID $lock_pid); refusing to overlap it."
                exit 1
            fi
            ;;
    esac
    if ! rmdir "$LOCK_DIR" 2>/dev/null || ! mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "Cannot acquire $LOCK_DIR; remove the stale lock only after confirming no update is running."
        exit 1
    fi
fi
printf '%s\n' "$$" > "$LOCK_DIR/pid"
trap release_lock EXIT
trap 'exit 130' HUP INT TERM

elapsed_status() {
    local elapsed=$SECONDS
    printf '%02d:%02d %s\n' "$((elapsed / 60))" "$((elapsed % 60))" "$1"
}

elapsed_status "Update starts"

if [ -x .venv312/bin/python ]; then
    export THEPYTHON=.venv312/bin/python
else
    export THEPYTHON=python3.12
fi
export PYTHONPATH=src:src/website:src/spinorama:.

# check meta
${THEPYTHON} ./scripts/check_meta.py
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO checking metadata ($status)";
    exit 1;
else
    elapsed_status "OK checking metadata"
fi

# update logos and speakers picture
./scripts/update_pictures.sh
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after updating pictures ($status)"
    exit 1
else
    elapsed_status "OK after updating pictures"
fi

# generate all graphs if some are missing
${THEPYTHON} ./scripts/generate_graphs.py --update-cache
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate graph!"
    exit 1;
else
    elapsed_status "OK after generate graph!"
fi

# recompute metadata for all speakers
${THEPYTHON} ./scripts/generate_meta.py
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate meta!"
    exit 1;
else
    elapsed_status "OK after generate meta!"
fi

# fetch missing headphone pictures
#command=$(${THEPYTHON} ./scripts/headphone_fetch_pictures.py 2>&1)
#status=$?
#if [ $status -ne 0 ]; then
#    echo "WARN: headphone picture fetch had failures (non-fatal)"
#else
#    echo "OK after headphone picture fetch!"
#fi

# generate headphone graphs
${THEPYTHON} ./scripts/generate_graphs.py --headphones
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "WARN: headphone graph generation had failures (non-fatal)"
else
    elapsed_status "OK after headphone graph generation!"
fi

# compute headphone EQs (requires autoeq binary)
if command -v autoeq &> /dev/null; then
    ./scripts/headphone_eqs_compute.sh
    status=$?
    if [ $status -ne 0 ]; then
        elapsed_status "WARN: headphone EQ computation had failures (non-fatal)"
    else
        elapsed_status "OK after headphone EQ computation!"
    fi
else
    elapsed_status "SKIP headphone EQ computation (autoeq binary not in PATH)"
fi

# generate eq filters
${THEPYTHON} ./scripts/generate_peqs.py --generate-images-only
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate eq filters!"
    exit 1;
else
    elapsed_status "OK after generate eq filters!"
fi

# generate radar
${THEPYTHON} ./scripts/generate_radar.py
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate radar!"
    exit 1;
else
    elapsed_status "OK after generate radar!"
fi

# generate eq_compare
${THEPYTHON} ./scripts/generate_eq_compare.py
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate EQ compare!"
    exit 1;
else
    elapsed_status "OK after generate EQ compare!"
fi

# generate status
today="$(date "+%Y-%m-%d")"
${THEPYTHON} ./scripts/generate_stats.py --print=eq_csv --log-level=ERROR > build/spinorama.org-${today}.csv 2>&1
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate statistics in csv!"
    exit 1;
else
    elapsed_status "OK after generate statistics in csv!"
fi

# generate list of svgs
${THEPYTHON} ./scripts/svg2symbols.py > build/website/symbols.html
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after update symbols!"
    rm -f build/website/symbols.html
    exit 1;
else
    elapsed_status "OK after update symbols"
fi

# generate list of brands
./scripts/update_brands.sh
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after update brands!"
    rm -f build/website/brands.html
    exit 1;
else
    elapsed_status "OK after update brands"
fi

# generate list of reviewers
./scripts/update_reviewers.sh
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after update reviewers!"
    rm -f build/website/reviewers.html
    exit 1;
else
    elapsed_status "OK after update reviewers"
fi

${THEPYTHON} ./scripts/generate_html.py --dev --optim --sitedev=https://dev.spinorama.org
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after generate HTML!"
    exit 1;
else
    elapsed_status "OK after generate HTML!"
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

./scripts/check_html.sh
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO after checking HTML!"
    exit 1;
else
    elapsed_status "OK after checking HTML!"
fi

# copy
./scripts/update_dev.sh
status=$?
if [ $status -ne 0 ]; then
    elapsed_status "KO Update $TARGET!"
    exit 1;
else
    elapsed_status "OK Update $TARGET!"
fi
elapsed_status "Update complete"
exit 0;
