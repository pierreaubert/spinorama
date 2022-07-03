#!/bin/bash
for d in datas/eq/*; do
    conf="$d/conf-autoeq.json";
    if ! test -f "$conf"; then
        speaker=$(basename "$d");
        lineversion=$(grep v0. "datas/eq/$speaker/iir-autoeq.txt")
        version=${lineversion##* }
        echo "run $speaker $version";
        current="$d/iir-autoeq.txt";
        if test -f "$current"; then
           cp "$current" "$d/iir-$version.txt";
        fi
        rm -f docs/speakers/"$speaker"/*.png ; 
        ./generate_peqs.py --speaker="$speaker" --force --verbose --smooth-measurements=5 --max-Q=3
    fi
done