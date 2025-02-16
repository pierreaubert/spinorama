#!/bin/bash

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 swap directory"
    exit 1
fi

name="$2"
swap="$1"

if ! [ -d "$name" ]; then
   echo "directory $name doesn't exist";
   exit 1
fi

if ! [ -f "$name/SPL Horizontal.txt" ]; then
   echo "Horizontal measurements don't exist in $name";
   exit 1
fi


if ! [ -f "$name/SPL Vertical.txt" ]; then
   echo "Horizontal measurements don't exist in $name";
   exit 1
fi

dir1="horizontal"
dir2="vertical"
if [ "$swap" != "horizontal" ] && [ "$swap" != "vertical" ]; then
    echo "Usage: $0 swap directory"
    echo "swap can be horizontal or vertical; true means measurement will move to a horizontal one, false the reverse"
    exit 1
elif [ "$swap" == "vertical" ]; then
    dir1="vertical"
    dir2="horizontal"
fi

git mv "${name}" "${name}-${dir1}"
mkdir -p "${name}-${dir2}"
# note the ^ to capitalise the first letter
cp "${name}-${dir1}/SPL ${dir1^}.txt" "${name}-${dir2}/SPL ${dir2^}.txt"
cp "${name}-${dir1}/SPL ${dir2^}.txt" "${name}-${dir2}/SPL ${dir1^}.txt"
