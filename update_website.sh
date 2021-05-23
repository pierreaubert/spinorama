#!/bin/bash
echo "Update starts"
export PYTHONPATH=src:.

IP="127.0.0.1"
if [ $HOSTNAME = "spin" ]; then
    IP="192.168.1.36"
fi

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
rm -f docs/compare/*.json
command=$(./generate_compare.py)
status=$?
if [ $status -ne 0 ]; then
    echo "KO after generate compare!"
    exit 1;
else
    echo "OK after generate compare!"
fi
# generate all jpg if some are missing
./update_pictures.sh
# generate stats
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
command=$(./check_html.py)
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

