#!/bin/sh

PATTERN='/^[0-9].*/ {printf("%f,%f,%f\n", $1, $2, $3)}'

for i in $2_hor_+*.txt; do
    j="${i#$2_hor_+}";
    awk "$PATTERN" "$i" > "../${j%.txt}"_H.txt;
done

for i in $2_ver_+*.txt; do
    j="${i#$2_ver_+}";
    awk "$PATTERN" "$i" > "../${j%.txt}"_V.txt;
done

for i in $2_hor_-*.txt; do
    j="${i#$2_hor_-}";
    awk "$PATTERN" "$i" > "../-${j%.txt}"_H.txt;
done

for i in $2_ver_-*.txt; do
    j="${i#$2_ver_-}";
    awk "$PATTERN" "$i" > "../-${j%.txt}"_V.txt;
done
