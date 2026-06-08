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

# fetch missing headphone pictures
#command=$(${THEPYTHON} ./scripts/headphone_fetch_pictures.py 2>&1)
#status=$?
#if [ $status -ne 0 ]; then
#    echo "WARN: headphone picture fetch had failures (non-fatal)"
#else
#    echo "OK after headphone picture fetch!"
#fi

${THEPYTHON} ./scripts/generate_headphone_datas.py
${THEPYTHON} ./scripts/generate_headphone_meta.py

# generate headphone graphs
command=$(${THEPYTHON} ./scripts/generate_graphs.py --headphones)
status=$?
if [ $status -ne 0 ]; then
    echo "WARN: headphone graph generation had failures (non-fatal)"
else
    echo "OK after headphone graph generation!"
fi

# compute headphone EQs (requires autoeq binary)
if command -v autoeq &> /dev/null; then
    command=$(./scripts/headphone_eqs_compute.sh)
    status=$?
    if [ $status -ne 0 ]; then
        echo "WARN: headphone EQ computation had failures (non-fatal)"
    else
        echo "OK after headphone EQ computation!"
    fi
else
    echo "SKIP headphone EQ computation (autoeq binary not in PATH)"
fi

command=$(${THEPYTHON} ./scripts/generate_html.py --dev --optim --sitedev=https://dev.spinorama.org)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate HTML!"
    exit 1;
else
    echo "OK after generate HTML!"
fi

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
