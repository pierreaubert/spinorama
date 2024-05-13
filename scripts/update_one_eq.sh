#!/bin/bash

./generate_graphs.py --speaker="$SPEAKER" --update-cache

mkdir -p "build/eqs/$SPEAKER"

rm -f "datas/eq/$SPEAKER/iir-autoeq.txt"
rm -f "docs/speakers/$SPEAKER"/*/filters_*

compute_eq()
{
    target_dir="build/eqs/$SPEAKER/$2-$1"

    mkdir -p "$target_dir"

    ./generate_peqs.py --verbose --force --optimisation=global --max-iter=15000 --dash-ip=192.168.1.37 --speaker="$SPEAKER" --max-peq=$1 --fitness=$2

    mkdir -p "$target_dir"
    mv "datas/eq/$SPEAKER/iir-autoeq.txt" "$target_dir"
    mv "docs/speakers/$SPEAKER"/*/filters_* "$target_dir"
}

compute_eq 3 "Flat"
compute_eq 4 "Flat"
compute_eq 5 "Flat"
compute_eq 6 "Flat"
compute_eq 7 "Flat"

compute_eq 3 "Score"
compute_eq 4 "Score"
compute_eq 5 "Score"
compute_eq 6 "Score"
compute_eq 7 "Score"

