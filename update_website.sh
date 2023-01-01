#!/bin/bash
# A library to display spinorama charts
#
# Copyright (C) 2020-23 Pierre Aubert pierreaubert(at)yahoo(dot)fr
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
export PYTHONPATH=src:src/website:src/spinorama:.

IP="127.0.0.1"
case $HOSTNAME in

    "spin")
        IP="192.168.88.20"
        ;;
    "7pi")
        IP="192.168.88.17"
        ;;
    "horn")
        IP="192.168.1.36"
        ;;
esac
#echo $IP

# check meta
command=$(./check_meta.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO checking metadata ($status)";
    exit 1;
else
    echo "OK checking metadata"
fi

# update logos and speakers picture
./update_pictures.sh
# generate all graphs if some are missing
rm -fr /tmp/ray
command=$(./generate_graphs.py --dash-ip="$IP")
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate graph!"
    exit 1;
else
    echo "OK after generate graph!"
fi
# recompute metadata for all speakers
rm -f docs/assets/metadata.json
command=$(./generate_meta.py  --dash-ip="$IP")
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate meta!"
    exit 1;
else
    echo "OK after generate meta!"
fi
# generate all jpg if some are missing
./update_pictures.sh
# generate radar
# rm -f docs/speakers/*/spider*
command=$(./generate_radar.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate radar!"
    exit 1;
else
    echo "OK after generate radar!"
fi
# generate status
rm -f docs/stats/*.json
command=$(./generate_stats.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate statistics!"
    exit 1;
else
    echo "OK after generate statistics!"
fi
# generate website
./update_brands.sh
./update_reviewers.sh
command=$(./generate_html.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate HTML!"
    exit 1;
else
    echo "OK after generate HTML!"
fi
command=$(./check_html.sh)
if [ $status -ne 0 ]; then
    echo "KO after checking HTML!"
    exit 1;
else
    echo "OK after checking HTML!"
fi
# copy
TARGET=$HOME/src/pierreaubert.github.io/spinorama
command=$(./update_sync.sh)
status=$?
if [ $status -ne 0 ]; then
    echo "KO Update $TARGET!"
    exit 1;
else
    echo "OK Update $TARGET!"
fi
# evaluate what's new and needs to be changed
cd ${TARGET} && git status
exit 0;
