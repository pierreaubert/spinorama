#!/bin/bash
for d in datas/eq/*; do
    speaker=$(basename "$d");
    lineversion=$(grep v0. "datas/eq/$speaker/iir-autoeq.txt")
    version=${lineversion##* }
    current="$d/iir-autoeq.txt";
    if test -f "$current"; then
        mv "$current" "$d/iir-$version.txt";
    fi
    rm -f dist/speakers/"$speaker"/*.png ;
done

./generate_peqs.py --force --verbose
